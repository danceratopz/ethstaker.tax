from sqlalchemy import Column, Boolean, LargeBinary, Numeric, Integer, Float, String, ForeignKey, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class Balance(Base):
    __tablename__ = "balance"

    slot = Column(Integer, nullable=False, primary_key=True)
    validator_index = Column(Integer, nullable=False, primary_key=True)
    balance = Column(Float(asdecimal=True), nullable=False)


class BlockReward(Base):
    __tablename__ = "block_reward"

    # A precision of 27 for the numeric type is enough to store the whole current supply of ETH, ~100M. Should be safe?

    slot = Column(Integer, nullable=False, primary_key=True, autoincrement=False)
    proposer_index = Column(Integer, nullable=True)
    fee_recipient = Column(String(length=42), nullable=True)
    priority_fees_wei = Column(Numeric(precision=27), nullable=True)
    block_extra_data = Column(LargeBinary)
    mev = Column(Boolean, nullable=True)
    mev_reward_recipient = Column(String(length=42), nullable=True)
    mev_reward_value_wei = Column(Numeric(precision=27), nullable=True)
    reward_processed_ok = Column(Boolean, nullable=False)


class RocketPoolBondReduction(Base):
    __tablename__ = "rocket_pool_bond_reduction"

    timestamp = Column(TIMESTAMP(timezone=True), nullable=True, primary_key=True)
    prev_node_fee = Column(Numeric(precision=19), nullable=False)
    prev_bond_value = Column(Numeric(precision=27), nullable=True)

    # Relationships
    minipool_address = Column(ForeignKey("rocket_pool_minipool.minipool_address"), primary_key=True)
    minipool = relationship("RocketPoolMinipool", back_populates="bond_reductions")


class RocketPoolMinipool(Base):
    __tablename__ = "rocket_pool_minipool"

    minipool_index = Column(Integer, nullable=False, primary_key=True)
    minipool_address = Column(String(length=42), nullable=False, unique=True, index=True)
    validator_index = Column(Integer, nullable=False, index=True)
    node_address = Column(String(length=42), nullable=False)
    node_deposit_balance = Column(String(length=20), nullable=False)
    fee = Column(Numeric(precision=19), nullable=False)

    # Relationships
    bond_reductions = relationship("RocketPoolBondReduction", back_populates="minipool")


class RocketPoolReward(Base):
    __tablename__ = "rocket_pool_reward"

    node_address = Column(String(length=42), nullable=False, primary_key=True)
    reward_collateral_rpl = Column(Numeric(precision=27), nullable=False)
    reward_smoothing_pool_wei = Column(Numeric(precision=27), nullable=False)

    # Relationships
    reward_period_index = Column(ForeignKey("rocket_pool_reward_period.reward_period_index"), primary_key=True)
    reward_period = relationship("RocketPoolRewardPeriod", back_populates="rewards")


class RocketPoolRewardPeriod(Base):
    __tablename__ = "rocket_pool_reward_period"

    reward_period_index = Column(Integer, nullable=False, primary_key=True)
    reward_period_end_time = Column(TIMESTAMP(timezone=True), nullable=False)

    # Relationships
    rewards = relationship("RocketPoolReward", back_populates="reward_period")


class Withdrawal(Base):
    __tablename__ = "withdrawal"

    slot = Column(Integer, nullable=False, primary_key=True)
    validator_index = Column(Integer, nullable=False, primary_key=True, index=True)
    amount_gwei = Column(Numeric(precision=18), nullable=True)

    # Relationships
    withdrawal_address_id = Column(ForeignKey("withdrawal_address.id"))
    withdrawal_address = relationship("WithdrawalAddress", back_populates="withdrawals")


class WithdrawalAddress(Base):
    __tablename__ = "withdrawal_address"

    id = Column(Integer, primary_key=True)
    address = Column(String(length=42), nullable=False)

    # Relationships
    withdrawals = relationship("Withdrawal", back_populates="withdrawal_address")

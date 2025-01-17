<script setup lang="ts">
import {computed, Ref, ref, watch} from 'vue'
import ValidatorAdder from "../components/inputs/ValidatorAdder.vue";
import CurrencyPicker from "../components/inputs/CurrencyPicker.vue";
import DateRangePicker from "../components/inputs/DateRangePicker.vue";
import {
  InvalidApiRequestResponse,
  PricesRequestParams,
  PricesResponse,
  RewardsRequest, RewardsResponse, RocketPoolNodeRewardForDate, RocketPoolValidatorRewards,
  ValidatorRewards,
} from "../types/rewards.ts";
import { parse, isInteger } from 'lossless-json'
import { downloadAsCsv } from '../components/outputs/csvDownload.ts'

import axios, {AxiosError} from "axios";
import IncomeChart from "../components/outputs/IncomeChart.vue";
import SummaryTable from "../components/outputs/SummaryTable.vue";
import {isRocketPoolValidatorRewards} from "../functions/rocketpool.ts";

let validatorIndexes: Ref<Set<number>> = ref(new Set([]));
let selectedCurrency = ref();
let startDateString = ref();
let endDateString = ref();

let rocketPoolNodeRewards: Ref<(RocketPoolNodeRewardForDate)[]> = ref([]);
let validatorRewardsData: Ref<(ValidatorRewards | RocketPoolValidatorRewards)[]> = ref([]);
let rewardsLoading = ref(false);

let useRocketPoolMode = ref(false);
let useConsensusIncomeOnWithdrawal = ref(true);
let csvDownloadGroupByDate = ref(false);

let priceDataEth: Ref<PricesResponse | undefined> = ref();
let priceDataRpl: Ref<PricesResponse | undefined> = ref();
let priceDataLoading = ref(false);


watch(selectedCurrency, async () => {
  if (validatorRewardsData.value.length == 0) return;
  await getPriceData();
})
watch(validatorRewardsData, async () => {
  if (validatorRewardsData.value.length == 0) return;
  await getPriceData();
})


async function getPriceData() {
  const pricesRequestParams: PricesRequestParams = {
    start_date: startDateString.value,
    end_date: endDateString.value,
    currency: selectedCurrency.value,
  }

  priceDataEth.value = undefined;
  priceDataRpl.value = undefined;
  priceDataLoading.value = true;

  try {
    const respEth = await axios.get("/api/v2/prices/ethereum", { params: pricesRequestParams });
    priceDataEth.value = respEth.data;
    const respRpl = await axios.get("/api/v2/prices/rocket-pool", { params: pricesRequestParams });
    priceDataRpl.value = respRpl.data;
  } catch (err: unknown) {
    let errorMessage: string
    if (axios.isAxiosError(err)) {
      errorMessage = `Failed to get prices - ${err.message}`;
    } else {
      errorMessage = `Unknown error occurred - ${err}`;
    }
    alert(errorMessage);
    throw err;
  } finally {
    priceDataLoading.value = false;
  }
}

async function getRewards() {
  const data: RewardsRequest = {
    validator_indexes: Array.from(validatorIndexes.value),
    start_date: startDateString.value,
    end_date: endDateString.value,
  }

  rocketPoolNodeRewards.value = [];
  validatorRewardsData.value = [];
  rewardsLoading.value = true;

  // parse integer values into a bigint, and use a regular number otherwise
  function customNumberParser(value: string) {
    // Ran into some issues using the default LosslessNumber type -> using BigInt
    return isInteger(value) ? BigInt(value) : parseFloat(value)
  }

  try {
    const resp: RewardsResponse = (await axios.post("/api/v2/rewards", data, {
      transformResponse: function (response) {
        // Parse using lossless-json library - the amounts are in wei and could be larger
        // than JS
        return parse(response, undefined, customNumberParser);
      }
    })).data;
    rocketPoolNodeRewards.value = resp.rocket_pool_node_rewards;
    validatorRewardsData.value = resp.validator_rewards;
  } catch (err: unknown) {
    let errorMessage: string
    if (axios.isAxiosError(err)) {
      if (err.response?.status === 422) {
        errorMessage = `Failed to get rewards - ${(((err as AxiosError).response?.data) as InvalidApiRequestResponse).detail[0].msg}`;
      } else {
        errorMessage = `Failed to get rewards - ${(err as AxiosError).message}`;
      }
    } else {
      errorMessage = `Unknown error occurred - ${err}`;
    }
    alert(errorMessage);
    throw err;
  } finally {
    rewardsLoading.value = false;
  }
}

const showOutputs = computed<boolean>(() => {
  if (validatorRewardsData.value.length == 0) return false;
  if (!priceDataEth.value) return false;
  if (!priceDataRpl.value) return false;
  if (priceDataEth.value?.prices.length == 0) return false;
  if (priceDataRpl.value?.prices.length == 0) return false;
  return true;
})

const enableRocketPoolModeToggle = computed<boolean>(() => {
  return validatorRewardsData.value.some(vr => isRocketPoolValidatorRewards(vr));
})

</script>

<template>
  <div class="container my-3">
    <h2>Add your validators here</h2>
    <ValidatorAdder @validator-indexes-changed="(newValidatorIndexes: Set<number>) => validatorIndexes = newValidatorIndexes"></ValidatorAdder>
  </div>
  <div class="container my-3">
    <div class="row">
      <div class="col">
        <h3>Pick a date range</h3>
        <DateRangePicker @date-range-changed="(newStartDate: string, newEndDate: string) => { startDateString = newStartDate; endDateString = newEndDate }"></DateRangePicker>
      </div>
      <div class="col">
        <h3>Select your currency</h3>
        <CurrencyPicker @selected-currency-changed="(newCurrency: string) => {selectedCurrency = newCurrency}"></CurrencyPicker>
      </div>
    </div>
  </div>
  <div class="container mt-3 text-center">
    <BButton
        variant="primary"
        @click.prevent="getRewards"
        :disabled="validatorIndexes.size == 0 || rewardsLoading || priceDataLoading"
        class="mx-1"
    >
      <div v-if="rewardsLoading || priceDataLoading" class="spinner-border spinner-border-sm" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <span v-else>
        <i class="bi-calculator"></i>
        Calculate
        <i
            class="bi-question-square mx-1"
            v-b-tooltip
            title='Wondering how this works? Find out <a href="#">here</a>'
        />
      </span>
    </BButton>
  </div>
  <div v-if="showOutputs" class="container border-top border-bottom py-2 mt-2">
    <div class="my-1 d-flex align-items-center">
      <BFormCheckbox v-model="useConsensusIncomeOnWithdrawal" switch>
        <span class="mx-1">Recognize consensus layer income upon withdrawal</span>
        <i
            class="bi-question-square"
            v-b-tooltip
            title="The default behavior of ethstaker.tax is to account for the consensus layer income
                   when the excess validator balance is withdrawn to the withdrawal address.
                   This toggle overrides this behavior and uses
                   the validator's end-of-day balance to determine consensus layer income
                   on a daily basis instead."
        />
      </BFormCheckbox>
    </div>
    <div class="my-1 d-flex align-items-center">
      <BFormCheckbox v-model="useRocketPoolMode" switch :disabled="!enableRocketPoolModeToggle">
        <img src="../assets/logo-rocket-pool.svg" alt="Logo Rocket Pool" height="30" :style="{
          opacity: useRocketPoolMode ? 1 : 0.3
        }" class="mx-1" />
        <span class="mx-1">Rocket Pool Mode</span>
        <i class="bi-question-square" v-b-tooltip title="<a href='#'>Learn More (coming soon)</a>"/>
      </BFormCheckbox>
    </div>
    <div class="my-1 d-flex align-items-center border-top pt-2 mb-0">
      <BButton
        class="mx-3"
        @click="downloadAsCsv(
            validatorRewardsData,
            rocketPoolNodeRewards,
            useConsensusIncomeOnWithdrawal,
            useRocketPoolMode,
            priceDataEth as PricesResponse,
            priceDataRpl as PricesResponse,
            csvDownloadGroupByDate,
            )"
        :disabled="validatorRewardsData.length == 0 || rewardsLoading || priceDataLoading"
        variant="secondary"
      >
        <span>
          <i class="bi-cloud-download me-1"></i>
          Download CSV for all validators
        </span>
      </BButton>
      <BFormCheckbox v-model="csvDownloadGroupByDate" switch>
        <span class="mx-1">Group By Date</span>
      </BFormCheckbox>
    </div>
  </div>
  <div class="container mt-3 mb-5">
    <div
      v-if="showOutputs"
      class="row d-flex align-items-center"
    >
      <div class="col-lg-6">
        <IncomeChart
            v-if="priceDataEth"
            :rewards-data="validatorRewardsData"
            :price-data-eth="priceDataEth"
            :currency="selectedCurrency"
            :use-consensus-income-on-withdrawal="useConsensusIncomeOnWithdrawal"
            :use-rocket-pool-mode="useRocketPoolMode"
            chart-container-height="300px"
            chart-container-width="100%"
        >
        </IncomeChart>
      </div>
      <div class="col-lg-6">
        <SummaryTable
            v-if="priceDataEth && priceDataRpl"
            :validator-rewards-data="validatorRewardsData"
            :rocket-pool-node-rewards="rocketPoolNodeRewards"
            :use-consensus-income-on-withdrawal="useConsensusIncomeOnWithdrawal"
            :use-rocket-pool-mode="useRocketPoolMode"
            :price-data-eth="priceDataEth"
            :price-data-rpl="priceDataRpl"
            :currency="selectedCurrency"
        >
        </SummaryTable>
      </div>
    </div>
  </div>
</template>

<style scoped>

h1 {
  margin-bottom: 1rem;
}

</style>

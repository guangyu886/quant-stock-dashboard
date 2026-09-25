<template>
  <div class="space-y-5">
    <div class="bg-slate-900/60 rounded-xl p-5 border border-slate-800/60">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <FilterInput v-model="filters.pe_max" label="市盈率 ≤" placeholder="如 20" />
        <FilterInput v-model="filters.pb_max" label="市净率 ≤" placeholder="如 3" />
        <FilterInput v-model="filters.roe_min" label="ROE ≥ (%)" placeholder="如 15" />
        <FilterInput v-model="filters.dividend_yield_min" label="股息率 ≥ (%)" placeholder="如 3" />
        <FilterInput v-model="filters.revenue_growth_min" label="营收增长 ≥ (%)" placeholder="如 10" />
        <FilterInput v-model="filters.net_profit_growth_min" label="利润增长 ≥ (%)" placeholder="如 10" />
        <FilterInput v-model="filters.market_cap_min" label="市值 ≥ (亿)" placeholder="如 100" />
        <div class="flex items-end">
          <button @click="doScreen"
            class="w-full py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition-colors">
            🔍 开始筛选
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="text-center py-12">
      <div class="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2"></div>
      <span class="text-slate-500">筛选中...</span>
    </div>
    <div v-else-if="error" class="text-center py-12">
      <p class="text-rose-400 mb-2">⚠️ 筛选失败</p>
      <p class="text-slate-500 text-sm">{{ error }}</p>
    </div>
    <div v-else-if="results.length" class="bg-slate-900/60 rounded-xl border border-slate-800/60 overflow-hidden">
      <div class="text-xs text-slate-500 p-3 pl-5 border-b border-slate-800">共 {{ results.length }} 只股票</div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-800 text-slate-400 text-left text-xs uppercase tracking-wider">
              <th class="p-3 pl-5">代码</th><th class="p-3">名称</th><th class="p-3">行业</th>
              <th class="p-3 text-right">PE</th><th class="p-3 text-right">PB</th>
              <th class="p-3 text-right">ROE%</th><th class="p-3 text-right pr-5">市值(亿)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in results" :key="row.symbol" class="border-b border-slate-800/40 hover:bg-slate-800/30">
              <td class="p-3 pl-5 font-mono text-xs text-slate-400">{{ row.symbol }}</td>
              <td class="p-3 font-medium text-white">{{ row.name }}</td>
              <td class="p-3 text-slate-500 text-xs">{{ row.industry || '-' }}</td>
              <td class="p-3 text-right font-mono text-cyan-400">{{ row.pe?.toFixed(1) || '-' }}</td>
              <td class="p-3 text-right font-mono">{{ row.pb?.toFixed(2) || '-' }}</td>
              <td class="p-3 text-right font-mono">{{ row.roe?.toFixed(1) || '-' }}</td>
              <td class="p-3 text-right font-mono text-slate-500 pr-5">{{ row.total_mv?.toFixed(0) || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="text-center py-12 text-slate-500">设置条件后点击筛选</div>
  </div>
</template>

<script setup>
import { ref, h } from 'vue'
import { screenStocks } from '../api'

const filters = ref({ pe_max: null, pb_max: null, roe_min: null, dividend_yield_min: null, revenue_growth_min: null, net_profit_growth_min: null, market_cap_min: null })
const results = ref([]); const loading = ref(false); const error = ref(null)

function FilterInput(props, { emit }) {
  return h('div', [
    h('label', { class: 'text-xs text-slate-500 block' }, props.label),
    h('input', {
      type: 'number', step: 'any', placeholder: props.placeholder,
      class: 'w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-white mt-1 text-sm outline-none focus:border-blue-500',
      value: props.modelValue,
      onInput: e => emit('update:modelValue', e.target.value ? +e.target.value : null)
    })
  ])
}
FilterInput.props = ['modelValue', 'label', 'placeholder']
FilterInput.emits = ['update:modelValue']

async function doScreen() {
  loading.value = true; error.value = null
  try {
    const params = {}
    Object.entries(filters.value).forEach(([k, v]) => { if (v !== null && v !== '') params[k] = v })
    const res = await screenStocks(params); results.value = res.data
    if (!res.data.length) error.value = '没有符合条件的结果'
  } catch (e) { error.value = e.message || '筛选请求失败' }
  finally { loading.value = false }
}
</script>

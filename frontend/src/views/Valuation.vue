<template>
  <div class="space-y-5">
    <!-- 加载/错误 -->
    <div v-if="loading" class="text-center py-20">
      <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3"></div>
      <p class="text-slate-500">加载估值数据...</p>
    </div>
    <div v-else-if="error" class="text-center py-20">
      <p class="text-rose-400 mb-2">⚠️ 数据加载失败</p>
      <p class="text-slate-500 text-sm mb-4">{{ error }}</p>
      <button @click="fetch" class="px-4 py-2 bg-blue-600 rounded-lg text-white text-sm hover:bg-blue-700">重试</button>
    </div>
    <template v-else>
    <div class="flex gap-3 items-center flex-wrap">
      <select v-model="market" class="bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-blue-500">
        <option value="A">A股</option><option value="HK">港股</option><option value="US">美股</option>
      </select>
      <select v-model="metric" class="bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white outline-none focus:border-blue-500">
        <option value="pe">市盈率 PE</option><option value="pb">市净率 PB</option>
      </select>
      <span class="text-xs text-slate-500">从低到高排序</span>
    </div>

    <div v-if="dist" class="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div v-for="s in stats" :key="s.label"
        class="bg-slate-900/60 rounded-xl p-4 border border-slate-800/60">
        <div class="text-xs text-slate-500">{{ s.label }}</div>
        <div class="text-xl font-bold mt-1" :class="s.color">{{ s.value ?? '-' }}</div>
      </div>
    </div>

    <div class="bg-slate-900/60 rounded-xl border border-slate-800/60 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-800 text-slate-400 text-left text-xs uppercase tracking-wider">
              <th class="p-3 pl-5">#</th><th class="p-3">代码</th><th class="p-3">名称</th>
              <th class="p-3">行业</th><th class="p-3 text-right">PE</th>
              <th class="p-3 text-right">PB</th><th class="p-3 text-right pr-5">总市值(亿)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in rankData" :key="row.symbol"
              class="border-b border-slate-800/40 hover:bg-slate-800/30 transition-colors">
              <td class="p-3 pl-5 text-slate-500 font-mono text-xs">{{ i + 1 }}</td>
              <td class="p-3 font-mono text-xs text-slate-400">{{ row.symbol }}</td>
              <td class="p-3 font-medium text-white">{{ row.name }}</td>
              <td class="p-3 text-slate-500 text-xs">{{ row.industry || '-' }}</td>
              <td class="p-3 text-right font-mono" :class="peColor(row.pe)">{{ row.pe?.toFixed(1) || '-' }}</td>
              <td class="p-3 text-right font-mono text-slate-300">{{ row.pb?.toFixed(2) || '-' }}</td>
              <td class="p-3 text-right font-mono text-slate-500 pr-5">{{ row.total_mv?.toFixed(0) || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { getValuationRank, getValuationDistribution } from '../api'

const market = ref('A'); const metric = ref('pe')
const rankData = ref([]); const dist = ref(null)
const loading = ref(true); const error = ref(null)

const stats = computed(() => [
  { label: '最低 PE', value: dist.value?.pe?.min, color: 'text-emerald-400' },
  { label: '中位数 PE', value: dist.value?.pe?.median, color: 'text-cyan-400' },
  { label: '平均 PE', value: dist.value?.pe?.mean, color: 'text-amber-400' },
  { label: '最高 PE', value: dist.value?.pe?.max, color: 'text-rose-400' },
])

function peColor(v) {
  if (!v) return 'text-slate-500'
  if (v <= 10) return 'text-emerald-400'
  if (v <= 20) return 'text-amber-400'
  if (v <= 30) return 'text-orange-400'
  return 'text-rose-400'
}

async function fetch() {
  loading.value = true; error.value = null
  try {
  const [rank, distribution] = await Promise.all([
    getValuationRank(market.value, metric.value, 50),
    getValuationDistribution(market.value)
  ])
  rankData.value = rank.data; dist.value = distribution.data
  } catch (e) { error.value = e.message || '网络错误，请稍后重试' }
  finally { loading.value = false }
}
onMounted(fetch); watch([market, metric], fetch)
</script>

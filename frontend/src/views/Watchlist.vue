<template>
  <div v-if="loading" class="text-center py-20">
    <div class="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3"></div>
    <p class="text-slate-500">加载自选股...</p>
  </div>
  <div v-else class="space-y-5">
    <!-- 添加 -->
    <div class="bg-slate-900/60 rounded-xl p-4 border border-slate-800/60">
      <div class="flex gap-3 items-end">
        <div class="flex-1">
          <label class="text-xs text-slate-500 block mb-1">股票代码</label>
          <input v-model="newSymbol" placeholder="如 sh600519"
            class="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500" />
        </div>
        <div class="w-48">
          <label class="text-xs text-slate-500 block mb-1">备注（可选）</label>
          <input v-model="newNote" placeholder="如：茅台"
            class="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm outline-none focus:border-blue-500" />
        </div>
        <button @click="addWatch"
          class="py-2 px-5 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition-colors">
          ➕ 添加
        </button>
      </div>
      <p v-if="addError" class="text-rose-400 text-xs mt-2">{{ addError }}</p>
      <p v-if="addSuccess" class="text-emerald-400 text-xs mt-2">{{ addSuccess }}</p>
    </div>

    <!-- 列表 -->
    <div v-if="watchlist.length" class="bg-slate-900/60 rounded-xl border border-slate-800/60 overflow-hidden">
      <div class="text-xs text-slate-500 p-3 pl-5 border-b border-slate-800">共 {{ watchlist.length }} 只自选股</div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-800 text-slate-400 text-left text-xs uppercase tracking-wider">
              <th class="p-3 pl-5">代码</th><th class="p-3">名称</th><th class="p-3">市场</th>
              <th class="p-3">备注</th><th class="p-3 text-right">添加日期</th>
              <th class="p-3 pr-5 text-center">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in watchlist" :key="row.symbol"
              class="border-b border-slate-800/40 hover:bg-slate-800/30 transition-colors">
              <td class="p-3 pl-5 font-mono text-xs text-slate-400">{{ row.symbol }}</td>
              <td class="p-3 font-medium text-white">{{ row.name || '-' }}</td>
              <td class="p-3 text-slate-500 text-xs">{{ row.market || '-' }}</td>
              <td class="p-3 text-slate-400 text-xs">{{ row.note || '-' }}</td>
              <td class="p-3 text-right text-slate-500 text-xs">{{ row.added_date || '-' }}</td>
              <td class="p-3 pr-5 text-center">
                <button @click="removeWatch(row.symbol)"
                  class="text-rose-400 hover:text-rose-300 text-xs transition-colors">🗑 移除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="text-center py-12 bg-slate-900/60 rounded-xl border border-slate-800/60">
      <p class="text-slate-500 mb-2">暂无自选股</p>
      <p class="text-slate-600 text-xs">在上方输入股票代码添加</p>
    </div>

    <!-- 估值概览 -->
    <div v-if="analysis.length" class="bg-slate-900/60 rounded-xl border border-slate-800/60 overflow-hidden">
      <div class="text-xs text-slate-500 p-3 pl-5 border-b border-slate-800">估值概览</div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-800 text-slate-400 text-left text-xs uppercase tracking-wider">
              <th class="p-3 pl-5">代码</th><th class="p-3">名称</th>
              <th class="p-3 text-right">PE</th><th class="p-3 text-right">PB</th>
              <th class="p-3 text-right pr-5">市值(亿)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in analysis" :key="row.symbol"
              class="border-b border-slate-800/40 hover:bg-slate-800/30">
              <td class="p-3 pl-5 font-mono text-xs text-slate-400">{{ row.symbol }}</td>
              <td class="p-3 font-medium text-white">{{ row.name || '-' }}</td>
              <td class="p-3 text-right font-mono text-cyan-400">{{ row.pe?.toFixed(1) || '-' }}</td>
              <td class="p-3 text-right font-mono">{{ row.pb?.toFixed(2) || '-' }}</td>
              <td class="p-3 text-right font-mono text-slate-500 pr-5">{{ row.total_mv?.toFixed(0) || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getWatchlist, addWatchlist, removeWatchlist, getWatchlistAnalysis } from '../api'

const watchlist = ref([])
const analysis = ref([])
const loading = ref(true)
const newSymbol = ref('')
const newNote = ref('')
const addError = ref('')
const addSuccess = ref('')

async function loadData() {
  loading.value = true
  try {
    const [wl, an] = await Promise.all([getWatchlist(), getWatchlistAnalysis()])
    watchlist.value = wl.data || []; analysis.value = an.data || []
  } catch (e) {
    watchlist.value = []; analysis.value = []
  }
  loading.value = false
}

async function addWatch() {
  const sym = newSymbol.value.trim()
  if (!sym) { addError.value = '请输入股票代码'; return }
  addError.value = ''; addSuccess.value = ''
  try {
    await addWatchlist(sym, newNote.value)
    addSuccess.value = `已添加 ${sym}`
    newSymbol.value = ''; newNote.value = ''
    loadData()
  } catch (e) {
    addError.value = e.response?.data?.detail || `添加失败: ${sym}`
  }
}

async function removeWatch(symbol) {
  try {
    await removeWatchlist(symbol)
    loadData()
  } catch (e) {
    addError.value = `移除失败: ${symbol}`
  }
}

onMounted(loadData)
</script>

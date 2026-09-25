import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 行情接口
export const getQuote = (symbol) => api.get(`/quote/${symbol}`)
export const getKline = (symbol, period = 'daily', limit = 250, indicators = 'ma,macd,rsi,boll,kdj') =>
  api.get(`/kline/${symbol}`, { params: { period, limit, indicators } })

// 估值接口
export const getValuationRank = (market = 'A', metric = 'pe', limit = 50) =>
  api.get('/valuation/rank', { params: { market, metric, limit } })
export const getValuationDistribution = (market = 'A') =>
  api.get('/valuation/distribution', { params: { market } })
export const getValuationDetail = (symbol) => api.get(`/valuation/${symbol}`)

// 市场情绪
export const getSentimentSummary = () => api.get('/sentiment/summary')
export const getFundFlow = (days = 30) => api.get('/sentiment/fund-flow', { params: { days } })
export const getMarketBreadth = (market = 'A', days = 30) =>
  api.get('/sentiment/breadth', { params: { market, days } })
export const getVix = (days = 30) => api.get('/sentiment/vix', { params: { days } })

// 筛选
export const screenStocks = (params) => api.get('/screener', { params })

// 自选股
export const getWatchlist = () => api.get('/watchlist')
export const addWatchlist = (symbol, note) => api.post(`/watchlist/${symbol}`, null, { params: { note } })
export const removeWatchlist = (symbol) => api.delete(`/watchlist/${symbol}`)
export const getWatchlistAnalysis = () => api.get('/watchlist/analysis')

// 系统
export const getSystemStatus = () => api.get('/system/status')
export const triggerCollect = (task) => api.post('/system/collect', null, { params: { task } })
export const getOverview = () => api.get('/overview')

export default api

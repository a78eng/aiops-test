<template>
  <div>
    <!-- 顶部指标卡片：数据来自后端 → Prometheus -->
    <el-row :gutter="16">
      <el-col :span="6" v-for="m in metricCards" :key="m.label">
        <el-card shadow="hover">
          <div class="metric-label">{{ m.label }}</div>
          <!-- 超阈值变红，实现告警可视化 -->
          <div class="metric-value" :style="{ color: m.alert ? '#f56c6c' : '#303133' }">{{ m.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图：ECharts 展示近 1 小时 CPU / 内存 -->
    <el-row :gutter="16" style="margin-top:16px">
      <el-col :span="12"><el-card><div ref="cpuChart" style="height:320px"></div></el-card></el-col>
      <el-col :span="12"><el-card><div ref="memChart" style="height:320px"></div></el-card></el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const metricCards = ref([
  { label: 'CPU 使用率', value: '-', alert: false },
  { label: '内存使用率', value: '-', alert: false },
  { label: '磁盘使用率', value: '-', alert: false },
  { label: 'GPU 显存使用', value: '-', alert: false }
])
const cpuChart = ref(null)
const memChart = ref(null)
let timer = null

// 拉取当前实时指标
async function loadMetrics() {
  try {
    const res = await api.get('/monitor/metrics')  // 后端返回 { cpu, mem, disk, gpu }
    metricCards.value[0].value = res.cpu + '%';   metricCards.value[0].alert = res.cpu > 80
    metricCards.value[1].value = res.mem + '%';   metricCards.value[1].alert = res.mem > 90
    metricCards.value[2].value = res.disk + '%';  metricCards.value[2].alert = res.disk > 85
    metricCards.value[3].value = res.gpu || '-'
  } catch (e) { console.error('指标拉取失败', e) }
}

// 拉取趋势数据绘制折线图
async function loadCharts() {
  try {
    const res = await api.get('/monitor/range', { params: { hours: 1 } })
    // res = { cpu: [{time, value}...], mem: [{time, value}...] }
    echarts.init(cpuChart.value).setOption({
      title: { text: 'CPU 使用率（近1小时）' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: res.cpu.map(i => i.time) },
      yAxis: { type: 'value', max: 100 },
      series: [{ type: 'line', smooth: true, areaStyle: {}, data: res.cpu.map(i => i.value) }]
    })
    echarts.init(memChart.value).setOption({
      title: { text: '内存使用率（近1小时）' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: res.mem.map(i => i.time) },
      yAxis: { type: 'value', max: 100 },
      series: [{ type: 'line', smooth: true, areaStyle: {}, data: res.mem.map(i => i.value) }]
    })
  } catch (e) { console.error('趋势拉取失败', e) }
}

onMounted(() => {
  loadMetrics()
  loadCharts()
  // 每 30 秒自动刷新实时指标，无需手动刷新页面
  timer = setInterval(loadMetrics, 30000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.metric-label { color: #909399; font-size: 14px; }
.metric-value { font-size: 30px; font-weight: bold; margin-top: 8px; }
</style>

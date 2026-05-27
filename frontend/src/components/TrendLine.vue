<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import type { Trend } from '@/types'
import * as echarts from 'echarts'

const props = defineProps<{ data: Trend }>()
const container = ref<HTMLDivElement>()

const options = computed(() => ({
  tooltip: { trigger: 'axis' as const },
  grid: { left: 50, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: 'category' as const,
    data: props.data.points.map(p => p.date.slice(5)),
    axisLabel: { fontSize: 10 },
  },
  yAxis: {
    type: 'value' as const,
    name: '累计积分',
    axisLabel: { fontSize: 10 },
  },
  series: [
    {
      type: 'line',
      data: props.data.points.map(p => p.cumulative_score),
      smooth: true,
      lineStyle: { color: '#f59e0b', width: 2 },
      itemStyle: { color: '#f59e0b' },
      areaStyle: { color: 'rgba(245, 158, 11, 0.1)' },
    },
  ],
}))

let chart: echarts.ECharts | null = null

onMounted(() => {
  if (container.value) {
    chart = echarts.init(container.value)
    chart.setOption(options.value)
  }
})

watch(() => props.data, () => {
  chart?.setOption(options.value)
}, { deep: true })
</script>

<template>
  <div ref="container" class="w-full h-64"></div>
</template>

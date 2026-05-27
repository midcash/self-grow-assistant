<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import type { HeatmapData } from '@/types'
import * as echarts from 'echarts'

const props = defineProps<{ data: HeatmapData }>()
const container = ref<HTMLDivElement>()

const options = computed(() => {
  const catList = props.data.categories
  const rows = props.data.data as Array<Record<string, unknown>>

  return {
    tooltip: {
      formatter: (p: unknown) => {
        const param = p as { dataIndex: number; seriesName: string; value: unknown }
        const d = rows[param.dataIndex] as Record<string, unknown>
        return `${d.date}<br/>${param.seriesName}: ${param.value}分钟`
      },
    },
    grid: { left: 60, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'category' as const,
      data: rows.map(d => String(d.date || '').slice(5)),
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: 'category' as const,
      data: catList,
      axisLabel: { fontSize: 11 },
    },
    visualMap: {
      min: 0,
      max: 120,
      calculable: true,
      orient: 'horizontal' as const,
      left: 'center',
      bottom: 0,
      inRange: { color: ['#fef3c7', '#f59e0b', '#d97706'] },
    },
    series: [{
      type: 'heatmap',
      data: catList.flatMap((cat, ci) =>
        rows.map((d, di) => [di, ci, (d as Record<string, number>)[cat] || 0])
      ),
      label: { show: false },
    }],
  }
})

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
  <div ref="container" class="w-full h-72"></div>
</template>

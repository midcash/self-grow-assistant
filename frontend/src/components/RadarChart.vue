<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import type { DashboardQuality } from '@/types'
import * as echarts from 'echarts'

const props = defineProps<{ qualities: DashboardQuality[] }>()
const container = ref<HTMLDivElement>()

const options = computed(() => ({
  radar: {
    center: ['50%', '55%'],
    radius: '65%',
    indicator: props.qualities.map(q => ({ name: q.name, max: 100 })),
    axisName: { fontSize: 11 },
  },
  series: [{
    type: 'radar',
    data: [{
      value: props.qualities.map(q => q.progress_pct),
      name: '当前进度',
      areaStyle: { color: 'rgba(245, 158, 11, 0.15)' },
      lineStyle: { color: '#f59e0b', width: 2 },
      itemStyle: { color: '#f59e0b' },
      symbol: 'circle',
      symbolSize: 4,
    }],
  }],
}))

let chart: echarts.ECharts | null = null

onMounted(() => {
  if (container.value) {
    chart = echarts.init(container.value)
    chart.setOption(options.value)
  }
})

watch(() => props.qualities, () => {
  chart?.setOption(options.value)
}, { deep: true })
</script>

<template>
  <div ref="container" class="w-full h-64"></div>
</template>

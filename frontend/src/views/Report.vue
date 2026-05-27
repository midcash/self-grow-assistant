<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getHeatmap, getTrend, getSummary } from '@/api/progress'
import { listQualities } from '@/api/qualities'
import type { HeatmapData, Trend, Summary, Quality } from '@/types'
import { formatLocalDate } from '@/utils/date'
import NavBar from '@/components/NavBar.vue'
import HeatmapVue from '@/components/Heatmap.vue'
import TrendLine from '@/components/TrendLine.vue'

const range = ref<'7' | '30'>('7')
const heatmap = ref<HeatmapData | null>(null)
const trend = ref<Trend | null>(null)
const summary = ref<Summary | null>(null)
const qualities = ref<Quality[]>([])
const selectedQuality = ref<number | null>(null)

function getStartDate(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days + 1)
  return formatLocalDate(d)
}

async function load() {
  const days = parseInt(range.value)
  const endDate = formatLocalDate()

  const [h, s] = await Promise.all([
    getHeatmap(getStartDate(days), endDate),
    getSummary('weekly', endDate),
  ])
  heatmap.value = h
  summary.value = s

  qualities.value = await listQualities()
  if (qualities.value.length && !selectedQuality.value) {
    selectedQuality.value = qualities.value[0].id
  }
  if (selectedQuality.value) {
    trend.value = await getTrend(selectedQuality.value, days)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-content px-4 pt-6">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-bold">成长报告</h1>
      <div class="flex gap-1 bg-gray-100 rounded-lg p-1">
        <button
          @click="range = '7'; load()"
          class="px-3 py-1 text-xs rounded-md transition-colors"
          :class="range === '7' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-400'"
        >7天</button>
        <button
          @click="range = '30'; load()"
          class="px-3 py-1 text-xs rounded-md transition-colors"
          :class="range === '30' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-400'"
        >30天</button>
      </div>
    </div>

    <div v-if="summary" class="bg-gradient-to-br from-amber-50 to-orange-50 rounded-xl p-4 mb-4">
      <p class="text-xs text-gray-400 mb-1">{{ summary.period }}</p>
      <div class="flex gap-4 text-sm mb-2">
        <span>投入 {{ summary.total_duration }} 分钟</span>
        <span>获得 {{ summary.total_score }} 积分</span>
        <span>连续 {{ summary.streak_days }} 天</span>
      </div>
      <p class="text-xs text-gray-500 leading-relaxed">{{ summary.insight }}</p>
    </div>

    <div v-if="heatmap" class="bg-white rounded-xl border border-gray-100 p-4 mb-4">
      <h2 class="text-sm font-medium text-gray-500 mb-2">每日投入热力图</h2>
      <HeatmapVue :data="heatmap" />
    </div>

    <div class="bg-white rounded-xl border border-gray-100 p-4 mb-4">
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-sm font-medium text-gray-500">品质趋势</h2>
        <select
          v-model="selectedQuality"
          @change="load"
          class="text-xs px-2 py-1 rounded border border-gray-200 outline-none"
        >
          <option v-for="q in qualities" :key="q.id" :value="q.id">{{ q.name }}</option>
        </select>
      </div>
      <TrendLine v-if="trend" :data="trend" />
      <div v-else class="text-center text-gray-300 text-sm py-8">请先创建品质目标</div>
    </div>

    <NavBar />
  </div>
</template>

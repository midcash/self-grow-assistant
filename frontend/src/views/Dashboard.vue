<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getDashboard } from '@/api/progress'
import { checkIn, skipTodo } from '@/api/todos'
import { get, upload } from '@/api/request'
import type { Dashboard } from '@/types'
import { formatLocalDate } from '@/utils/date'
import NavBar from '@/components/NavBar.vue'
import QualityCard from '@/components/QualityCard.vue'
import TodoItem from '@/components/TodoItem.vue'
import RadarChart from '@/components/RadarChart.vue'

const route = useRoute()
const today = ref(formatLocalDate())
const dashboard = ref<Dashboard | null>(null)
const loading = ref(false)
const bgUrl = ref<string | null>(null)
const bgOrientation = ref<string>('landscape')
const bgUploading = ref(false)
const bgError = ref(false)

async function load() {
  loading.value = true
  dashboard.value = await getDashboard(today.value)
  loading.value = false
}

async function loadBackground() {
  const data = await get<{ image_url: string | null; orientation: string }>('/dashboard/background')
  bgUrl.value = data.image_url
  bgOrientation.value = data.orientation || 'landscape'
}

async function handleCheckIn(id: number) {
  await checkIn(id)
  await load()
}

async function handleSkip(id: number) {
  await skipTodo(id)
  await load()
}

function triggerBgUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/jpeg,image/png,image/webp,image/gif'
  input.onchange = async (e: Event) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    bgUploading.value = true
    bgError.value = false
    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await upload<{ image_url: string; orientation: string }>('/dashboard/background', formData)
      bgUrl.value = result.image_url
      bgOrientation.value = result.orientation || 'landscape'
    } catch {
      bgError.value = true
    } finally {
      bgUploading.value = false
    }
  }
  input.click()
}

onMounted(() => {
  load()
  loadBackground()
})

// Reload when navigating back to this page
watch(() => route.path, (path) => {
  if (path === '/') load()
})
</script>

<template>
  <div class="page-content">
    <!-- Header -->
    <div class="px-4 pt-6 pb-4">
      <div class="flex items-center justify-between">
        <h1 class="text-xl font-bold">看板</h1>
        <input
          type="date"
          v-model="today"
          @change="load()"
          class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm outline-none focus:border-amber-400"
        />
      </div>
      <div class="flex gap-4 mt-2 text-xs text-gray-500">
        <span>完成率 {{ dashboard ? Math.round(dashboard.completion_rate * 100) : 0 }}%</span>
        <span>投入 {{ dashboard?.total_duration || 0 }} 分钟</span>
        <span>连续 {{ dashboard?.streak_days || 0 }} 天</span>
        <span>今日 +{{ dashboard?.total_score_today || 0 }} 积分</span>
      </div>
    </div>

    <!-- Background Banner -->
    <div class="px-4 mt-4">
      <div
        :class="['relative w-full rounded-xl overflow-hidden bg-gradient-to-br from-amber-100 via-amber-50 to-orange-100 flex items-center justify-center cursor-pointer group', bgOrientation === 'portrait' ? 'h-96' : 'h-40']"
        @click="triggerBgUpload"
      >
        <img
          v-if="bgUrl && !bgError"
          :src="bgUrl"
          class="absolute inset-0 w-full h-full object-cover"
          @error="bgError = true"
        />
        <div v-if="!bgUrl || bgError" class="text-center z-10">
          <svg class="w-8 h-8 text-amber-300 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <p class="text-amber-400 text-sm">点击上传背景图，激发学习动力</p>
        </div>
        <!-- Hover overlay -->
        <div
          v-if="bgUrl && !bgError"
          class="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10"
        >
          <span class="text-white text-sm">更换背景</span>
        </div>
        <!-- Uploading spinner -->
        <div
          v-if="bgUploading"
          class="absolute inset-0 bg-white/60 flex items-center justify-center z-20"
        >
          <svg class="w-6 h-6 text-amber-500 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      </div>
    </div>

    <!-- Radar Chart -->
    <div v-if="dashboard?.qualities.length" class="px-2">
      <RadarChart :qualities="dashboard.qualities" />
    </div>
    <div v-else class="px-4 py-8 text-center text-gray-400 text-sm">
      还没有品质目标，去「品质」页创建一个吧
    </div>

    <!-- Quality Cards -->
    <div class="px-4 mt-2 space-y-2">
      <QualityCard
        v-for="q in dashboard?.qualities || []"
        :key="q.id"
        :quality="q"
      />
    </div>

    <!-- Today's TODOs -->
    <div class="px-4 mt-6">
      <h2 class="text-sm font-medium text-gray-500 mb-3">{{ today }} 任务</h2>
      <div v-if="dashboard?.todos.length" class="space-y-2">
        <TodoItem
          v-for="t in dashboard.todos"
          :key="t.id"
          :todo="t"
          @checkin="handleCheckIn"
          @skip="handleSkip"
        />
      </div>
      <div v-else class="text-center text-gray-300 text-sm py-8">
        今天还没有任务，去「录入」页添加吧
      </div>
    </div>

    <NavBar />
  </div>
</template>

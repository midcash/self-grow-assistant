<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get, post, upload } from '@/api/request'
import type { RoleModel, RoleModelQuality, AdoptResult } from '@/types'
import NavBar from '@/components/NavBar.vue'

const models = ref<RoleModel[]>([])
const expanded = ref<number | null>(null)
const adoptingId = ref<number | null>(null)
const adopted = ref<Set<number>>(new Set())
const messages = ref<Map<number, string>>(new Map())
const uploadingId = ref<number | null>(null)
const imageErrors = ref<Set<number>>(new Set())

onMounted(async () => {
  models.value = await get<RoleModel[]>('/role-models')
})

function toggleExpand(id: number) {
  expanded.value = expanded.value === id ? null : id
}

async function adopt(roleModelId: number, qualityId: number) {
  adoptingId.value = qualityId
  try {
    const result = await post<AdoptResult>(`/role-models/${roleModelId}/adopt/${qualityId}`)
    adopted.value.add(qualityId)
    messages.value.set(qualityId, result.message)
  } catch {
    messages.value.set(qualityId, '操作失败，请重试')
  } finally {
    adoptingId.value = null
  }
}

function getImageUrl(model: RoleModel): string {
  if (!model.image_url || imageErrors.value.has(model.id)) return ''
  if (model.image_url.startsWith('http')) return model.image_url
  return model.image_url
}

function onImageError(id: number) {
  imageErrors.value.add(id)
}

function triggerUpload(roleModelId: number) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/jpeg,image/png,image/webp,image/gif'
  input.onchange = async (e: Event) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    uploadingId.value = roleModelId
    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await upload<{ image_url: string }>(`/role-models/${roleModelId}/upload-image`, formData)
      const model = models.value.find(m => m.id === roleModelId)
      if (model) {
        model.image_url = result.image_url
        imageErrors.value.delete(roleModelId)
      }
    } catch {
      // upload failed, keep fallback
    } finally {
      uploadingId.value = null
    }
  }
  input.click()
}

const avatarIcons: Record<string, string> = {
  theater: 'M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  heart: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z',
  smile: 'M14.828 14.828a4 4 0 01-5.656 0M10 9h.01M14 9h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  star: 'M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z',
  sun: 'M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z',
  award: 'M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z',
  flame: 'M17.657 18.657A8 8 0 016.343 7.343S7 9 9 10c0-2 .5-5 2.986-7C14 5 16.09 5.777 17.656 7.343A7.975 7.975 0 0120 13a7.975 7.975 0 01-2.343 5.657z',
  rocket: 'M15.59 14.37a6 6 0 01-5.84 7.38v-4.8m5.84-2.58a14.98 14.98 0 006.16-12.12A14.98 14.98 0 009.631 8.41m5.96 5.96a14.926 14.926 0 01-5.841 2.58m-.119-8.54a6 6 0 00-7.381 5.84h4.8m2.581-5.84a14.927 14.927 0 00-2.58 5.84m2.699 2.7c-.103.021-.207.041-.311.06a15.09 15.09 0 01-2.448-2.448 14.9 14.9 0 01.06-.312m-2.24 2.39a4.493 4.493 0 00-1.757 4.306 4.493 4.493 0 004.306-1.758M16.5 9a1.5 1.5 0 11-3 0 1.5 1.5 0 013 0z',
  user: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
  shield: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z',
}

const categoryColors: Record<string, string> = {
  '学习': 'bg-blue-50 text-blue-700',
  '运动': 'bg-green-50 text-green-700',
  '工作': 'bg-slate-50 text-slate-700',
  '生活': 'bg-amber-50 text-amber-700',
  '阅读': 'bg-purple-50 text-purple-700',
  '冥想': 'bg-indigo-50 text-indigo-700',
}

const qualityIcons: Record<string, string> = {
  '高情商': 'speech',
  '待人诚恳': 'hands',
  '落落大方': 'sparkles',
  '自律坚持': 'clock',
  '真诚自信': 'badge',
  '真实做自己': 'face',
  '清醒自省': 'eye',
  '终身热爱': 'flame',
  '大胆追梦': 'rocket',
  '温柔善良': 'heart',
  '踏实敬业': 'shield',
  '坚韧不拔': 'mountain',
  '自我和解': 'peace',
}
</script>

<template>
  <div class="max-w-[480px] mx-auto px-4 pt-6 pb-24">
    <h1 class="text-lg font-bold text-gray-800 mb-1">明星榜样</h1>
    <p class="text-sm text-gray-400 mb-5">以他们的闪光品质为镜子，让成长有迹可循</p>

    <div class="space-y-3">
      <div
        v-for="model in models"
        :key="model.id"
        class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden transition-all"
      >
        <!-- Card Header -->
        <button
          class="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
          @click="toggleExpand(model.id)"
        >
          <div class="flex-shrink-0 w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center overflow-hidden relative group">
            <img
              v-if="getImageUrl(model)"
              :src="getImageUrl(model)"
              :alt="model.name"
              class="w-full h-full object-cover"
              @error="onImageError(model.id)"
            />
            <svg v-else class="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" :d="avatarIcons[model.avatar] || avatarIcons.user" />
            </svg>
            <div
              class="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
              @click.stop="triggerUpload(model.id)"
            >
              <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div
              v-if="uploadingId === model.id"
              class="absolute inset-0 bg-white/60 flex items-center justify-center"
            >
              <svg class="w-4 h-4 text-amber-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
          </div>
          <div class="flex-1 min-w-0">
            <div class="font-medium text-gray-800 text-sm">{{ model.name }}</div>
            <div class="text-xs text-gray-400">{{ model.field }}</div>
          </div>
          <svg
            class="w-5 h-5 text-gray-300 transition-transform"
            :class="{ 'rotate-180': expanded === model.id }"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <!-- Expanded Qualities -->
        <div v-if="expanded === model.id" class="border-t border-gray-50 px-4 py-3 space-y-3 bg-gray-50/30">
          <p class="text-xs text-gray-500 leading-relaxed">{{ model.description }}</p>

          <div
            v-for="q in model.qualities"
            :key="q.id"
            class="bg-white rounded-lg p-3 border border-gray-100"
          >
            <div class="flex items-center gap-2 mb-2">
              <span class="text-sm font-semibold text-gray-800">{{ q.quality_name }}</span>
              <span class="text-[10px] text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
                {{ q.suggested_activities.length }} 项推荐活动
              </span>
            </div>
            <p class="text-xs text-gray-500 mb-3 leading-relaxed">{{ q.description }}</p>

            <!-- Suggested Activities -->
            <div class="space-y-1.5 mb-3">
              <div
                v-for="(act, idx) in q.suggested_activities"
                :key="idx"
                class="flex items-start gap-2 text-xs"
              >
                <span class="text-amber-400 mt-0.5">&middot;</span>
                <div class="flex-1">
                  <span class="text-gray-700">{{ act.content }}</span>
                  <div class="flex gap-2 mt-0.5">
                    <span class="px-1.5 py-0.5 rounded text-[10px]" :class="categoryColors[act.category] || 'bg-gray-50 text-gray-500'">
                      {{ act.category }}
                    </span>
                    <span class="text-gray-400">{{ act.duration_minutes }}分钟/{{ act.frequency }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Adopt Button -->
            <button
              v-if="!adopted.has(q.id)"
              class="w-full py-2 rounded-lg text-sm font-medium transition-colors"
              :class="adoptingId === q.id ? 'bg-gray-100 text-gray-400' : 'bg-amber-500 text-white hover:bg-amber-600 active:scale-[0.98]'"
              :disabled="adoptingId === q.id"
              @click="adopt(model.id, q.id)"
            >
              {{ adoptingId === q.id ? '创建中...' : '以此为榜样' }}
            </button>
            <div v-else class="w-full py-2 rounded-lg text-sm font-medium text-center bg-green-50 text-green-600">
              {{ messages.get(q.id) || '已创建品质目标' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="models.length === 0" class="text-center py-20 text-gray-300 text-sm">
      加载中...
    </div>

    <NavBar />
  </div>
</template>

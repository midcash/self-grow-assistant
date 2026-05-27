<script setup lang="ts">
import type { DashboardQuality } from '@/types'

defineProps<{ quality: DashboardQuality }>()
</script>

<template>
  <div class="bg-white rounded-xl border border-gray-100 p-4 shadow-sm">
    <div class="flex items-center justify-between mb-2">
      <div class="flex items-center gap-2">
        <span class="text-lg">{{ quality.icon === 'star' ? '&#9733;' : quality.icon }}</span>
        <span class="font-medium text-sm">{{ quality.name }}</span>
      </div>
      <span class="text-xs text-gray-400">{{ quality.level_name }}</span>
    </div>

    <div class="relative w-full h-2 bg-gray-100 rounded-full overflow-hidden mb-2">
      <div
        class="absolute inset-y-0 left-0 bg-amber-400 rounded-full transition-all duration-500"
        :style="{ width: Math.min(quality.progress_pct, 100) + '%' }"
      ></div>
    </div>

    <div class="flex justify-between text-xs text-gray-400">
      <span>{{ quality.current_score }} 积分</span>
      <span>距「{{ quality.next_level_name }}」还需 {{ quality.next_level_score - quality.current_score }} 分</span>
    </div>
  </div>
</template>

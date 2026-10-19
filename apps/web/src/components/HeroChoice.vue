<script setup lang="ts">
import { ref } from 'vue'
import { CircleCheck, Search, Upload } from 'lucide-vue-next'

export type HeroChoiceValue = 'find' | 'list'

const model = defineModel<HeroChoiceValue>({ required: true })

const options = [
  { value: 'find', title: 'Find a Property', text: 'Search verified homes and land', icon: Search },
  { value: 'list', title: 'List My Property', text: 'Upload and manage listings', icon: Upload },
] as const

const optionEls = ref<HTMLButtonElement[]>([])

function onKeydown(event: KeyboardEvent, index: number): void {
  const forward = event.key === 'ArrowRight' || event.key === 'ArrowDown'
  const backward = event.key === 'ArrowLeft' || event.key === 'ArrowUp'
  if (!forward && !backward) return
  event.preventDefault()
  const next = (index + (forward ? 1 : -1) + options.length) % options.length
  model.value = options[next].value
  optionEls.value[next]?.focus()
}
</script>

<template>
  <div role="radiogroup" aria-label="How will you use Axora?" class="grid gap-3 sm:grid-cols-2">
    <button
      v-for="(option, index) in options"
      :key="option.value"
      ref="optionEls"
      type="button"
      role="radio"
      :aria-checked="model === option.value"
      :tabindex="model === option.value ? 0 : -1"
      class="relative flex min-h-32 flex-col items-start gap-2 rounded-2xl border-2 bg-white p-4 text-left text-ink transition-colors duration-200 ease-out"
      :class="model === option.value ? 'border-ink' : 'border-white hover:border-ink/40'"
      @click="model = option.value"
      @keydown="onKeydown($event, index)"
    >
      <component :is="option.icon" class="size-7 text-brand" aria-hidden="true" />
      <span class="text-lg font-bold leading-tight">{{ option.title }}</span>
      <span class="text-sm text-muted">{{ option.text }}</span>
      <CircleCheck
        v-if="model === option.value"
        class="absolute right-3 top-3 size-6 text-brand"
        aria-hidden="true"
      />
    </button>
  </div>
</template>

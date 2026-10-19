<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import gsap from 'gsap'
import { useScrollLock } from '@vueuse/core'
import { Check, Copy, X } from 'lucide-vue-next'
import { formatNaira } from '@/lib/money'
import { prefersReducedMotion } from '@/plugins/motion'
import type { PaymentAccount } from '@/types'

const props = defineProps<{ open: boolean; account: PaymentAccount | null }>()
const emit = defineEmits<{ close: [] }>()

const overlayEl = ref<HTMLElement | null>(null)
const dialogEl = ref<HTMLElement | null>(null)
const closeEl = ref<HTMLButtonElement | null>(null)
const rendered = ref(false) // stays in the DOM while the exit animation runs
const copiedKey = ref('')
const scrollLock = useScrollLock(document.body)

let opener: HTMLElement | null = null
let copiedTimer: number | undefined

function animateIn(): void {
  if (prefersReducedMotion() || !overlayEl.value || !dialogEl.value) return
  gsap.fromTo(overlayEl.value, { opacity: 0 }, { opacity: 1, duration: 0.2, ease: 'power2.out' })
  gsap.fromTo(
    dialogEl.value,
    { opacity: 0, y: 16, scale: 0.98 },
    { opacity: 1, y: 0, scale: 1, duration: 0.22, ease: 'power2.out' },
  )
}

function animateOut(done: () => void): void {
  if (prefersReducedMotion() || !overlayEl.value) {
    done()
    return
  }
  gsap.to(overlayEl.value, { opacity: 0, duration: 0.15, ease: 'power2.out', onComplete: done })
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen && props.account) {
      opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
      rendered.value = true
      scrollLock.value = true
      await nextTick()
      animateIn()
      closeEl.value?.focus()
    } else if (rendered.value) {
      animateOut(() => {
        rendered.value = false
        scrollLock.value = false
        opener?.focus()
      })
    }
  },
  { immediate: true },
)

function trapFocus(event: KeyboardEvent): void {
  if (event.key !== 'Tab' || !dialogEl.value) return
  const focusable = dialogEl.value.querySelectorAll<HTMLElement>('button:not([disabled]), [href], input, select, textarea')
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

async function copyValue(key: string, value: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(value)
    copiedKey.value = key
    window.clearTimeout(copiedTimer)
    copiedTimer = window.setTimeout(() => {
      copiedKey.value = ''
    }, 1800)
  } catch {
    /* clipboard blocked; the number is still on screen to copy by hand */
  }
}

onBeforeUnmount(() => {
  window.clearTimeout(copiedTimer)
  scrollLock.value = false
  if (overlayEl.value) gsap.killTweensOf([overlayEl.value, dialogEl.value])
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="rendered && account"
      ref="overlayEl"
      class="fixed inset-0 z-50 grid place-items-end bg-black/60 sm:place-items-center sm:p-4"
      @click.self="emit('close')"
      @keydown.esc.stop="emit('close')"
      @keydown="trapFocus"
    >
      <div
        ref="dialogEl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="account-title"
        class="max-h-dvh w-full max-w-md overflow-y-auto rounded-t-3xl bg-white p-6 text-ink sm:rounded-3xl"
        style="padding-bottom: max(1.5rem, env(safe-area-inset-bottom))"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 id="account-title" class="text-2xl font-extrabold">Pay by bank transfer</h2>
            <p class="mt-1 text-muted">Send exactly this amount to the official Axora Finds account.</p>
          </div>
          <button
            ref="closeEl"
            type="button"
            class="-mr-2 -mt-2 grid size-11 shrink-0 place-items-center rounded-full hover:bg-line"
            aria-label="Close"
            @click="emit('close')"
          >
            <X class="size-6" aria-hidden="true" />
          </button>
        </div>

        <p class="mt-5 rounded-2xl border border-line p-4 text-center">
          <span class="block text-sm text-muted">Inspection fee</span>
          <span class="font-display text-3xl font-extrabold text-black">{{ formatNaira(account.amount) }}</span>
        </p>

        <dl class="mt-5 divide-y divide-line">
          <div class="py-3">
            <dt class="text-sm text-muted">Account name</dt>
            <dd class="font-semibold">{{ account.account_name }}</dd>
          </div>
          <div class="py-3">
            <dt class="text-sm text-muted">Bank</dt>
            <dd class="font-semibold">{{ account.bank_name }}</dd>
          </div>
          <div class="flex items-center justify-between gap-3 py-3">
            <div>
              <dt class="text-sm text-muted">Account number</dt>
              <dd class="font-display text-2xl font-extrabold tracking-wide">{{ account.account_number }}</dd>
            </div>
            <button type="button" class="btn btn-outline px-4" @click="copyValue('number', account.account_number)">
              <Check v-if="copiedKey === 'number'" class="size-5" aria-hidden="true" />
              <Copy v-else class="size-5" aria-hidden="true" />
              {{ copiedKey === 'number' ? 'Copied' : 'Copy' }}
            </button>
          </div>
          <div class="flex items-center justify-between gap-3 py-3">
            <div>
              <dt class="text-sm text-muted">Payment reference</dt>
              <dd class="font-semibold tracking-wide">{{ account.reference }}</dd>
            </div>
            <button type="button" class="btn btn-outline px-4" @click="copyValue('reference', account.reference)">
              <Check v-if="copiedKey === 'reference'" class="size-5" aria-hidden="true" />
              <Copy v-else class="size-5" aria-hidden="true" />
              {{ copiedKey === 'reference' ? 'Copied' : 'Copy' }}
            </button>
          </div>
        </dl>

        <p v-if="account.note" class="mt-2 text-sm text-muted">{{ account.note }}</p>
        <p class="mt-3 text-sm text-muted">
          Your request stays pending. Our team confirms the inspection only after the payment is verified.
        </p>

        <button type="button" class="btn btn-primary mt-6 w-full" @click="emit('close')">Done</button>
      </div>
    </div>
  </Teleport>
</template>

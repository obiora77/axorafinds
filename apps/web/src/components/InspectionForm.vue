<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useForm } from 'vee-validate'
import { z } from 'zod'
import gsap from 'gsap'
import { CircleCheck, HandCoins, Landmark } from 'lucide-vue-next'
import AccountModal from '@/components/AccountModal.vue'
import { apiFetch, parseApiError } from '@/lib/api'
import { formatNaira, hasFee } from '@/lib/money'
import { toFormSchema } from '@/lib/validate'
import { prefersReducedMotion } from '@/plugins/motion'
import { useAuthStore } from '@/stores/auth'
import type { InspectionResult, PaymentAccount } from '@/types'

const props = defineProps<{ property: { id: number; title: string; inspection_fee: string } }>()

const auth = useAuthStore()
// The parent keys this component by property id, so the fee is fixed for its lifetime.
const feeApplies = hasFee(props.property.inspection_fee)

function todayISO(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

const schema = z
  .object({
    name: z.string().trim().min(2, 'Enter your full name.'),
    phone: z.string().trim().regex(/^\+?[0-9 ()-]{10,20}$/, 'Enter a valid phone number.'),
    email: z.string().trim().email('Enter a valid email address.'),
    date: z
      .string()
      .min(1, 'Choose a preferred date.')
      .refine((value) => value >= todayISO(), 'Choose today or a later date.'),
    note: z.string().max(500, 'Keep the note under 500 characters.'),
    payment_choice: z.enum(['transfer', 'in_person']).optional(),
  })
  .superRefine((value, ctx) => {
    if (feeApplies && !value.payment_choice) {
      ctx.addIssue({ code: 'custom', path: ['payment_choice'], message: 'Choose how you will pay the inspection fee.' })
    }
  })

const { defineField, errors, handleSubmit, resetForm, setErrors, isSubmitting } = useForm({
  validationSchema: toFormSchema(schema),
  initialValues: {
    name: auth.user?.name ?? '',
    phone: auth.user?.phone ?? '',
    email: auth.user?.email ?? '',
    date: '',
    note: '',
    payment_choice: undefined,
  },
})

// Show an error after the field is left, then re-check as the person fixes it.
const lazy = (state: { errors: string[] }) => ({ validateOnModelUpdate: state.errors.length > 0 })
const [name, nameAttrs] = defineField('name', lazy)
const [phone, phoneAttrs] = defineField('phone', lazy)
const [email, emailAttrs] = defineField('email', lazy)
const [date, dateAttrs] = defineField('date', lazy)
const [note, noteAttrs] = defineField('note', lazy)
const [paymentChoice] = defineField('payment_choice')

const minDate = todayISO()
const submitError = ref('')
const result = ref<InspectionResult | null>(null)
const account = ref<PaymentAccount | null>(null)
const accountError = ref('')
const modalOpen = ref(false)
const successEl = ref<HTMLElement | null>(null)
const successIcon = ref<HTMLElement | null>(null)

async function loadAccount(inspection: InspectionResult): Promise<void> {
  accountError.value = ''
  try {
    // The server returns the bank details only for the request that was just created.
    account.value = await apiFetch<PaymentAccount>('/payments/account', {
      headers: { 'X-Inspection-Token': inspection.payment_token ?? '' },
    })
    modalOpen.value = true
  } catch (e) {
    accountError.value = parseApiError(e).message
  }
}

function playSuccess(): void {
  if (prefersReducedMotion() || !successEl.value) return
  gsap.fromTo(successEl.value, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.22, ease: 'power2.out' })
  if (successIcon.value) {
    gsap.fromTo(successIcon.value, { scale: 0.6 }, { scale: 1, duration: 0.2, ease: 'power2.out', delay: 0.05 })
  }
}

const onSubmit = handleSubmit(async (values) => {
  submitError.value = ''
  try {
    const created = await apiFetch<InspectionResult>('/inspections', {
      method: 'POST',
      auth: false,
      body: {
        name: values.name,
        phone: values.phone,
        email: values.email,
        property: props.property.id,
        date: values.date,
        note: values.note,
        ...(feeApplies ? { payment_choice: values.payment_choice } : {}),
      },
    })
    result.value = created
    await nextTick()
    playSuccess()
    successEl.value?.focus({ preventScroll: false })
    if (created.payment_choice === 'transfer' && created.payment_token) {
      await loadAccount(created)
    }
  } catch (e) {
    const parsed = parseApiError(e)
    submitError.value = parsed.message
    if (Object.keys(parsed.fields).length) setErrors(parsed.fields)
  }
})

function startOver(): void {
  result.value = null
  account.value = null
  accountError.value = ''
  resetForm()
}
</script>

<template>
  <section id="inspection" aria-labelledby="inspection-title" class="scroll-mt-24">
    <div
      v-if="result"
      ref="successEl"
      tabindex="-1"
      role="status"
      class="rounded-2xl border border-line bg-white p-5 outline-none"
    >
      <div ref="successIcon" class="inline-block">
        <CircleCheck class="size-10 text-brand" aria-hidden="true" />
      </div>
      <h2 id="inspection-title" class="mt-3 text-2xl font-extrabold">Request received</h2>
      <p class="mt-2">
        Your inspection request for <strong>{{ property.title }}</strong> is <strong>pending</strong>. Reference
        <strong>{{ result.reference }}</strong>.
      </p>
      <p class="mt-2 text-muted">
        We will contact you on {{ result.phone }} or {{ result.email }}. The visit is confirmed only after the request<template v-if="result.payment_status !== 'not_required'"> and the inspection fee</template>
        have been verified.
      </p>

      <template v-if="result.payment_choice === 'in_person' && result.payment_status !== 'not_required'">
        <p class="mt-3 rounded-xl border border-line p-3">
          You chose to pay in person. Your request is stored as unpaid and unconfirmed until our team verifies payment.
        </p>
      </template>

      <template v-if="result.payment_choice === 'transfer' && result.payment_status !== 'not_required'">
        <p v-if="accountError" class="mt-3 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">
          {{ accountError }} Our team will share the payment details with you.
        </p>
        <button v-if="account" type="button" class="btn btn-primary mt-4 w-full" @click="modalOpen = true">
          View payment details
        </button>
      </template>

      <button type="button" class="btn btn-outline mt-4 w-full" @click="startOver">Send another request</button>
    </div>

    <form v-else class="rounded-2xl border border-line bg-white p-5" novalidate @submit.prevent="onSubmit">
      <h2 id="inspection-title" class="text-2xl font-extrabold">Request inspection</h2>
      <p class="mt-1 text-muted">We confirm your visit once your request is verified.</p>

      <div class="mt-4 rounded-xl border border-line p-3">
        <template v-if="feeApplies">
          <span class="text-sm text-muted">Inspection fee</span>
          <span class="block font-display text-2xl font-extrabold text-black">{{ formatNaira(property.inspection_fee) }}</span>
        </template>
        <span v-else class="font-semibold">No inspection fee for this property.</span>
      </div>

      <div class="mt-5 space-y-4">
        <div>
          <label for="insp-name" class="label">Full name</label>
          <input id="insp-name" v-model="name" v-bind="nameAttrs" type="text" autocomplete="name" class="input" :aria-invalid="Boolean(errors.name)" :aria-describedby="errors.name ? 'insp-name-error' : undefined" />
          <p v-if="errors.name" id="insp-name-error" class="field-error">{{ errors.name }}</p>
        </div>
        <div>
          <label for="insp-phone" class="label">Phone number</label>
          <input id="insp-phone" v-model="phone" v-bind="phoneAttrs" type="tel" inputmode="tel" autocomplete="tel" placeholder="07012345678" class="input" :aria-invalid="Boolean(errors.phone)" :aria-describedby="errors.phone ? 'insp-phone-error' : undefined" />
          <p v-if="errors.phone" id="insp-phone-error" class="field-error">{{ errors.phone }}</p>
        </div>
        <div>
          <label for="insp-email" class="label">Email</label>
          <input id="insp-email" v-model="email" v-bind="emailAttrs" type="email" inputmode="email" autocomplete="email" class="input" :aria-invalid="Boolean(errors.email)" :aria-describedby="errors.email ? 'insp-email-error' : undefined" />
          <p v-if="errors.email" id="insp-email-error" class="field-error">{{ errors.email }}</p>
        </div>
        <div>
          <label for="insp-date" class="label">Preferred date</label>
          <input id="insp-date" v-model="date" v-bind="dateAttrs" type="date" :min="minDate" class="input" :aria-invalid="Boolean(errors.date)" :aria-describedby="errors.date ? 'insp-date-error' : undefined" />
          <p v-if="errors.date" id="insp-date-error" class="field-error">{{ errors.date }}</p>
        </div>
        <div>
          <label for="insp-note" class="label">Note <span class="font-normal text-muted">(optional)</span></label>
          <textarea id="insp-note" v-model="note" v-bind="noteAttrs" rows="3" maxlength="500" class="input" :aria-invalid="Boolean(errors.note)" :aria-describedby="errors.note ? 'insp-note-error' : undefined" />
          <p v-if="errors.note" id="insp-note-error" class="field-error">{{ errors.note }}</p>
        </div>

        <fieldset v-if="feeApplies">
          <legend class="label">How will you pay the inspection fee?</legend>
          <div class="grid gap-2">
            <label class="flex min-h-14 cursor-pointer items-start gap-3 rounded-xl border border-line p-3 has-[:checked]:border-ink">
              <input v-model="paymentChoice" type="radio" value="transfer" name="payment_choice" class="mt-1 size-5 accent-brand" />
              <span>
                <span class="flex items-center gap-2 font-semibold"><Landmark class="size-5" aria-hidden="true" />Bank transfer</span>
                <span class="text-sm text-muted">You get the official account after you submit.</span>
              </span>
            </label>
            <label class="flex min-h-14 cursor-pointer items-start gap-3 rounded-xl border border-line p-3 has-[:checked]:border-ink">
              <input v-model="paymentChoice" type="radio" value="in_person" name="payment_choice" class="mt-1 size-5 accent-brand" />
              <span>
                <span class="flex items-center gap-2 font-semibold"><HandCoins class="size-5" aria-hidden="true" />Pay in person</span>
                <span class="text-sm text-muted">A request only. It stays unpaid until staff verify payment.</span>
              </span>
            </label>
          </div>
          <p v-if="errors.payment_choice" class="field-error">{{ errors.payment_choice }}</p>
        </fieldset>
      </div>

      <p v-if="submitError" class="mt-4 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">
        {{ submitError }}
      </p>

      <button type="submit" class="btn btn-primary mt-5 w-full" :disabled="isSubmitting">
        {{ isSubmitting ? 'Sending request...' : 'Request inspection' }}
      </button>
    </form>

    <AccountModal :open="modalOpen" :account="account" @close="modalOpen = false" />
  </section>
</template>

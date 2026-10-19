<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useForm } from 'vee-validate'
import { z } from 'zod'
import gsap from 'gsap'
import { CircleCheck, Mail, MapPin, Phone } from 'lucide-vue-next'
import { apiFetch, parseApiError } from '@/lib/api'
import { SITE } from '@/lib/site'
import { toFormSchema } from '@/lib/validate'
import { prefersReducedMotion, reveal } from '@/plugins/motion'

const sent = ref(false)
const submitError = ref('')
const successEl = ref<HTMLElement | null>(null)

const schema = z.object({
  name: z.string().trim().min(2, 'Enter your name.'),
  email: z.string().trim().email('Enter a valid email address.'),
  message: z.string().trim().min(10, 'Write at least 10 characters.').max(2000, 'Keep the message under 2000 characters.'),
})

const { defineField, errors, handleSubmit, isSubmitting, resetForm, setErrors } = useForm({
  validationSchema: toFormSchema(schema),
  initialValues: { name: '', email: '', message: '' },
})
const lazy = (state: { errors: string[] }) => ({ validateOnModelUpdate: state.errors.length > 0 })
const [name, nameAttrs] = defineField('name', lazy)
const [email, emailAttrs] = defineField('email', lazy)
const [message, messageAttrs] = defineField('message', lazy)

const onSubmit = handleSubmit(async (values) => {
  submitError.value = ''
  try {
    await apiFetch('/contact', { method: 'POST', auth: false, body: values })
    sent.value = true
    await nextTick()
    if (!prefersReducedMotion() && successEl.value) {
      gsap.fromTo(successEl.value, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.22, ease: 'power2.out' })
    }
    successEl.value?.focus()
  } catch (e) {
    const parsed = parseApiError(e)
    submitError.value = parsed.message
    if (Object.keys(parsed.fields).length) setErrors(parsed.fields)
  }
})

function another(): void {
  sent.value = false
  resetForm()
}
</script>

<template>
  <div>
    <section class="on-red text-white" aria-labelledby="contact-title">
      <div class="page-wrap py-10 lg:py-14">
        <h1 id="contact-title" class="text-4xl font-extrabold sm:text-5xl">Contact us</h1>
        <p class="mt-3 max-w-xl text-lg">Questions about a listing, an inspection or listing your property? Reach the team.</p>
      </div>
    </section>

    <section class="panel">
      <div class="page-wrap grid gap-10 py-10 lg:grid-cols-[360px_minmax(0,1fr)] lg:py-14">
        <div v-motion v-bind="reveal()">
          <h2 class="text-2xl font-extrabold">Get in touch</h2>
          <ul class="mt-4 space-y-2">
            <li>
              <a :href="`mailto:${SITE.email}`" class="flex min-h-11 items-center gap-3 font-semibold hover:underline">
                <Mail class="size-6 shrink-0 text-brand" aria-hidden="true" />{{ SITE.email }}
              </a>
            </li>
            <li>
              <a :href="`tel:${SITE.phone}`" class="flex min-h-11 items-center gap-3 font-semibold hover:underline">
                <Phone class="size-6 shrink-0 text-brand" aria-hidden="true" />{{ SITE.phone }}
              </a>
            </li>
            <li class="flex min-h-11 items-center gap-3 font-semibold">
              <MapPin class="size-6 shrink-0 text-brand" aria-hidden="true" />{{ SITE.location }}
            </li>
          </ul>
        </div>

        <div v-motion v-bind="reveal(60)">
          <div v-if="sent" ref="successEl" tabindex="-1" role="status" class="rounded-2xl border border-line p-6 outline-none">
            <CircleCheck class="size-10 text-brand" aria-hidden="true" />
            <h2 class="mt-3 text-2xl font-extrabold">Message sent</h2>
            <p class="mt-2 text-muted">Thank you. Our team will reply by email.</p>
            <button type="button" class="btn btn-outline mt-4" @click="another">Send another message</button>
          </div>

          <form v-else class="rounded-2xl border border-line p-5 sm:p-6" novalidate @submit.prevent="onSubmit">
            <h2 class="text-2xl font-extrabold">Send a message</h2>
            <div class="mt-4 space-y-4">
              <div>
                <label for="contact-name" class="label">Name</label>
                <input id="contact-name" v-model="name" v-bind="nameAttrs" type="text" autocomplete="name" class="input" :aria-invalid="Boolean(errors.name)" :aria-describedby="errors.name ? 'contact-name-error' : undefined" />
                <p v-if="errors.name" id="contact-name-error" class="field-error">{{ errors.name }}</p>
              </div>
              <div>
                <label for="contact-email" class="label">Email</label>
                <input id="contact-email" v-model="email" v-bind="emailAttrs" type="email" inputmode="email" autocomplete="email" class="input" :aria-invalid="Boolean(errors.email)" :aria-describedby="errors.email ? 'contact-email-error' : undefined" />
                <p v-if="errors.email" id="contact-email-error" class="field-error">{{ errors.email }}</p>
              </div>
              <div>
                <label for="contact-message" class="label">Message</label>
                <textarea id="contact-message" v-model="message" v-bind="messageAttrs" rows="5" maxlength="2000" class="input" :aria-invalid="Boolean(errors.message)" :aria-describedby="errors.message ? 'contact-message-error' : undefined" />
                <p v-if="errors.message" id="contact-message-error" class="field-error">{{ errors.message }}</p>
              </div>
            </div>
            <p v-if="submitError" class="mt-4 rounded-xl border border-brand p-3 font-medium text-brand" role="alert">{{ submitError }}</p>
            <button type="submit" class="btn btn-primary mt-5 w-full sm:w-auto sm:px-10" :disabled="isSubmitting">
              {{ isSubmitting ? 'Sending...' : 'Send message' }}
            </button>
          </form>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref } from 'vue'
import { useForm } from 'vee-validate'
import { z } from 'zod'
import gsap from 'gsap'
import { CircleCheck, X } from 'lucide-vue-next'
import { parseApiError } from '@/lib/api'
import { NG_STATES, PROPERTY_TYPES } from '@/lib/site'
import { toFormSchema } from '@/lib/validate'
import { prefersReducedMotion } from '@/plugins/motion'
import { useAuthStore } from '@/stores/auth'
import { usePropertiesStore } from '@/stores/properties'

const MAX_PHOTOS = 8
const MAX_BYTES = 5 * 1024 * 1024

const auth = useAuthStore()
const store = usePropertiesStore()

const amount = (message: string) =>
  z.string().trim().regex(/^\d+(\.\d{1,2})?$/, message)

const schema = z.object({
  title: z.string().trim().min(5, 'Enter a title of at least 5 characters.').max(120, 'Keep the title under 120 characters.'),
  property_type: z.string().min(1, 'Choose a type.'),
  price: amount('Enter the rent as a number, for example 300000.').refine((v) => Number(v) > 0, 'Rent must be more than zero.'),
  bedrooms: z.string().trim().regex(/^\d{1,2}$/, 'Enter a whole number, 0 or more.'),
  bathrooms: z.string().trim().regex(/^\d{1,2}$/, 'Enter a whole number, 0 or more.'),
  state: z.string().min(1, 'Choose a state.'),
  city: z.string().trim().min(2, 'Enter the city or town.'),
  address: z.string().trim().max(200, 'Keep the address under 200 characters.'),
  description: z.string().trim().min(20, 'Describe the property in at least 20 characters.').max(4000, 'Keep the description under 4000 characters.'),
  amenities: z.string().trim().max(600, 'Keep amenities under 600 characters.'),
  inspection_fee: amount('Enter the fee as a number, or 0 for no fee.'),
})

const { defineField, errors, handleSubmit, isSubmitting, resetForm, setErrors } = useForm({
  validationSchema: toFormSchema(schema),
  initialValues: {
    title: '', property_type: '', price: '', bedrooms: '1', bathrooms: '1', state: '', city: '',
    address: '', description: '', amenities: '', inspection_fee: '0',
  },
})
const lazy = (state: { errors: string[] }) => ({ validateOnModelUpdate: state.errors.length > 0 })
const [title, titleAttrs] = defineField('title', lazy)
const [propertyType, propertyTypeAttrs] = defineField('property_type', lazy)
const [price, priceAttrs] = defineField('price', lazy)
const [bedrooms, bedroomsAttrs] = defineField('bedrooms', lazy)
const [bathrooms, bathroomsAttrs] = defineField('bathrooms', lazy)
const [state, stateAttrs] = defineField('state', lazy)
const [city, cityAttrs] = defineField('city', lazy)
const [address, addressAttrs] = defineField('address', lazy)
const [description, descriptionAttrs] = defineField('description', lazy)
const [amenities, amenitiesAttrs] = defineField('amenities', lazy)
const [inspectionFee, inspectionFeeAttrs] = defineField('inspection_fee', lazy)

// Photos are handled outside vee-validate because they are File objects.
const files = ref<File[]>([])
const previews = ref<string[]>([])
const photoError = ref('')
const submitError = ref('')
const submitted = ref(false)
const successEl = ref<HTMLElement | null>(null)

function addFiles(event: Event): void {
  const input = event.target as HTMLInputElement
  photoError.value = ''
  for (const file of Array.from(input.files ?? [])) {
    if (!file.type.startsWith('image/')) {
      photoError.value = `${file.name} is not an image.`
      continue
    }
    if (file.size > MAX_BYTES) {
      photoError.value = `${file.name} is larger than 5 MB.`
      continue
    }
    if (files.value.length >= MAX_PHOTOS) {
      photoError.value = `You can add up to ${MAX_PHOTOS} photos.`
      break
    }
    files.value.push(file)
    previews.value.push(URL.createObjectURL(file))
  }
  input.value = '' // lets the same file be picked again after removing it
}

function removePhoto(index: number): void {
  URL.revokeObjectURL(previews.value[index])
  files.value.splice(index, 1)
  previews.value.splice(index, 1)
}

function clearPhotos(): void {
  previews.value.forEach((url) => URL.revokeObjectURL(url))
  files.value = []
  previews.value = []
}

onBeforeUnmount(clearPhotos)

const onValid = handleSubmit(async (values) => {
  if (!files.value.length) {
    photoError.value = 'Add at least one photo.'
    return
  }
  submitError.value = ''
  const body = new FormData()
  body.append('title', values.title)
  body.append('property_type', values.property_type)
  body.append('price', values.price)
  body.append('bedrooms', values.bedrooms)
  body.append('bathrooms', values.bathrooms)
  body.append('state', values.state)
  body.append('city', values.city)
  body.append('address', values.address)
  body.append('description', values.description)
  body.append('inspection_fee', values.inspection_fee)
  values.amenities
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((item) => body.append('amenities', item))
  files.value.forEach((file) => body.append('photos', file))

  try {
    await store.create(body)
    submitted.value = true
    await nextTick()
    if (!prefersReducedMotion() && successEl.value) {
      gsap.fromTo(successEl.value, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.22, ease: 'power2.out' })
    }
    successEl.value?.focus()
  } catch (e) {
    const parsed = parseApiError(e)
    submitError.value = parsed.message
    const { photos, ...rest } = parsed.fields
    if (photos) photoError.value = photos
    if (Object.keys(rest).length) setErrors(rest)
  }
})

async function onSubmit(): Promise<void> {
  photoError.value = files.value.length ? '' : 'Add at least one photo.'
  await onValid()
}

function listAnother(): void {
  submitted.value = false
  clearPhotos()
  resetForm()
}
</script>

<template>
  <div class="pt-3 sm:pt-5">
    <section class="panel" aria-labelledby="list-title">
      <div class="page-wrap max-w-3xl py-8 lg:py-10">
        <h1 id="list-title" class="text-3xl font-extrabold sm:text-4xl">List a property</h1>

        <div v-if="!auth.isOwner" class="mt-6 rounded-2xl border border-line p-6">
          <h2 class="text-xl font-bold">You need an owner account to list a property</h2>
          <p class="mt-2 text-muted">
            You are signed in with a {{ auth.role }} account. Create an owner account with a different email to submit listings.
          </p>
          <button type="button" class="btn btn-outline mt-4" @click="auth.logout()">Logout and sign up as an owner</button>
        </div>

        <div v-else-if="submitted" ref="successEl" tabindex="-1" role="status" class="mt-6 rounded-2xl border border-line p-6 outline-none">
          <CircleCheck class="size-10 text-brand" aria-hidden="true" />
          <h2 class="mt-3 text-2xl font-extrabold">Listing submitted</h2>
          <p class="mt-2 text-lg">
            Your listing is <strong>pending review</strong>. It stays hidden until our team publishes it.
          </p>
          <div class="mt-5 flex flex-col gap-3 sm:flex-row">
            <button type="button" class="btn btn-primary" @click="listAnother">List another property</button>
            <RouterLink to="/properties" class="btn btn-outline">Browse properties</RouterLink>
          </div>
        </div>

        <template v-else>
          <p class="mt-1 text-muted">Listings are reviewed by our team and go live only after they are published.</p>

          <form class="mt-6 grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="onSubmit">
            <div class="sm:col-span-2">
              <label for="lp-title" class="label">Title</label>
              <input id="lp-title" v-model="title" v-bind="titleAttrs" type="text" class="input" placeholder="Spacious 2 bedroom flat at Fegge" :aria-invalid="Boolean(errors.title)" :aria-describedby="errors.title ? 'lp-title-error' : undefined" />
              <p v-if="errors.title" id="lp-title-error" class="field-error">{{ errors.title }}</p>
            </div>

            <div>
              <label for="lp-type" class="label">Type</label>
              <select id="lp-type" v-model="propertyType" v-bind="propertyTypeAttrs" class="input" :aria-invalid="Boolean(errors.property_type)" :aria-describedby="errors.property_type ? 'lp-type-error' : undefined">
                <option value="" disabled>Choose a type</option>
                <option v-for="type in PROPERTY_TYPES" :key="type.value" :value="type.value">{{ type.label }}</option>
              </select>
              <p v-if="errors.property_type" id="lp-type-error" class="field-error">{{ errors.property_type }}</p>
            </div>
            <div>
              <label for="lp-price" class="label">Rent (NGN)</label>
              <input id="lp-price" v-model="price" v-bind="priceAttrs" type="text" inputmode="decimal" placeholder="300000" class="input" :aria-invalid="Boolean(errors.price)" :aria-describedby="errors.price ? 'lp-price-error' : undefined" />
              <p v-if="errors.price" id="lp-price-error" class="field-error">{{ errors.price }}</p>
            </div>

            <div>
              <label for="lp-bedrooms" class="label">Bedrooms or rooms</label>
              <input id="lp-bedrooms" v-model="bedrooms" v-bind="bedroomsAttrs" type="text" inputmode="numeric" class="input" :aria-invalid="Boolean(errors.bedrooms)" :aria-describedby="errors.bedrooms ? 'lp-bedrooms-error' : undefined" />
              <p v-if="errors.bedrooms" id="lp-bedrooms-error" class="field-error">{{ errors.bedrooms }}</p>
            </div>
            <div>
              <label for="lp-bathrooms" class="label">Bathrooms</label>
              <input id="lp-bathrooms" v-model="bathrooms" v-bind="bathroomsAttrs" type="text" inputmode="numeric" class="input" :aria-invalid="Boolean(errors.bathrooms)" :aria-describedby="errors.bathrooms ? 'lp-bathrooms-error' : undefined" />
              <p v-if="errors.bathrooms" id="lp-bathrooms-error" class="field-error">{{ errors.bathrooms }}</p>
            </div>

            <div>
              <label for="lp-state" class="label">State</label>
              <select id="lp-state" v-model="state" v-bind="stateAttrs" class="input" :aria-invalid="Boolean(errors.state)" :aria-describedby="errors.state ? 'lp-state-error' : undefined">
                <option value="" disabled>Choose a state</option>
                <option v-for="item in NG_STATES" :key="item" :value="item">{{ item }}</option>
              </select>
              <p v-if="errors.state" id="lp-state-error" class="field-error">{{ errors.state }}</p>
            </div>
            <div>
              <label for="lp-city" class="label">City or town</label>
              <input id="lp-city" v-model="city" v-bind="cityAttrs" type="text" class="input" :aria-invalid="Boolean(errors.city)" :aria-describedby="errors.city ? 'lp-city-error' : undefined" />
              <p v-if="errors.city" id="lp-city-error" class="field-error">{{ errors.city }}</p>
            </div>

            <div class="sm:col-span-2">
              <label for="lp-address" class="label">Street or area <span class="font-normal text-muted">(optional)</span></label>
              <input id="lp-address" v-model="address" v-bind="addressAttrs" type="text" class="input" :aria-invalid="Boolean(errors.address)" :aria-describedby="errors.address ? 'lp-address-error' : undefined" />
              <p v-if="errors.address" id="lp-address-error" class="field-error">{{ errors.address }}</p>
            </div>

            <div class="sm:col-span-2">
              <label for="lp-description" class="label">Description</label>
              <textarea id="lp-description" v-model="description" v-bind="descriptionAttrs" rows="5" class="input" :aria-invalid="Boolean(errors.description)" :aria-describedby="errors.description ? 'lp-description-error' : undefined" />
              <p v-if="errors.description" id="lp-description-error" class="field-error">{{ errors.description }}</p>
            </div>

            <div class="sm:col-span-2">
              <label for="lp-amenities" class="label">Amenities <span class="font-normal text-muted">(optional)</span></label>
              <input id="lp-amenities" v-model="amenities" v-bind="amenitiesAttrs" type="text" class="input" placeholder="Borehole water, Prepaid meter, Fenced compound" aria-describedby="lp-amenities-hint" :aria-invalid="Boolean(errors.amenities)" />
              <p id="lp-amenities-hint" class="hint">Separate each one with a comma.</p>
              <p v-if="errors.amenities" class="field-error">{{ errors.amenities }}</p>
            </div>

            <div class="sm:col-span-2">
              <label for="lp-fee" class="label">Inspection fee (NGN)</label>
              <input id="lp-fee" v-model="inspectionFee" v-bind="inspectionFeeAttrs" type="text" inputmode="decimal" class="input sm:max-w-xs" aria-describedby="lp-fee-hint" :aria-invalid="Boolean(errors.inspection_fee)" />
              <p id="lp-fee-hint" class="hint">Enter 0 if visitors can inspect for free.</p>
              <p v-if="errors.inspection_fee" class="field-error">{{ errors.inspection_fee }}</p>
            </div>

            <div class="sm:col-span-2">
              <label for="lp-photos" class="label">Photos</label>
              <input
                id="lp-photos"
                type="file"
                accept="image/*"
                multiple
                class="block w-full text-base file:mr-3 file:min-h-11 file:cursor-pointer file:rounded-full file:border-0 file:bg-brand file:px-5 file:font-semibold file:text-white hover:file:bg-brand-dark"
                aria-describedby="lp-photos-hint"
                @change="addFiles"
              />
              <p id="lp-photos-hint" class="hint">Up to {{ MAX_PHOTOS }} photos, 5 MB each. The first photo is the cover.</p>
              <p v-if="photoError" class="field-error" role="alert">{{ photoError }}</p>
              <ul v-if="previews.length" class="mt-3 flex flex-wrap gap-3">
                <li v-for="(url, index) in previews" :key="url" class="relative">
                  <img :src="url" :alt="`Selected photo ${index + 1}`" width="96" height="96" class="size-24 rounded-xl object-cover" />
                  <button type="button" class="absolute -right-2 -top-2 grid size-11 place-items-center" :aria-label="`Remove photo ${index + 1}`" @click="removePhoto(index)">
                    <span class="grid size-7 place-items-center rounded-full bg-ink text-white"><X class="size-4" aria-hidden="true" /></span>
                  </button>
                </li>
              </ul>
            </div>

            <p v-if="submitError" class="rounded-xl border border-brand p-3 font-medium text-brand sm:col-span-2" role="alert">{{ submitError }}</p>

            <div class="sm:col-span-2">
              <button type="submit" class="btn btn-primary w-full sm:w-auto sm:px-10" :disabled="isSubmitting">
                {{ isSubmitting ? 'Submitting...' : 'Submit for review' }}
              </button>
            </div>
          </form>
        </template>
      </div>
    </section>
  </div>
</template>

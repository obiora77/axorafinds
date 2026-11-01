<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { FetchError } from 'ofetch'
import { CircleCheck, Pause, Play, Quote, Star } from 'lucide-vue-next'
import { apiFetch, parseApiError } from '@/lib/api'
import { prefersReducedMotion, reveal } from '@/plugins/motion'
import { useAuthStore } from '@/stores/auth'
import type { ReviewSummary } from '@/types'

const auth = useAuthStore()

const summary = ref<ReviewSummary | null>(null)
const loading = ref(true)
const error = ref('')
const showForm = ref(false)
const rating = ref(5)
const location = ref('')
const text = ref('')
const submitting = ref(false)
const submitError = ref('')
const submitted = ref(false)

const reviews = computed(() => summary.value?.results ?? [])
const averageStars = computed(() => {
  const average = summary.value?.average_rating
  return average == null ? 0 : Math.round(average)
})

const reduceMotion = prefersReducedMotion()
const paused = ref(false)

// Repeat short lists so each half of the marquee is wider than the page.
const copiesPerHalf = computed(() => {
  const count = reviews.value.length
  return count === 0 ? 1 : Math.max(1, Math.ceil(4 / count))
})
const halfReviews = computed(() =>
  Array.from({ length: copiesPerHalf.value }, () => reviews.value).flat(),
)
const shouldAnimate = computed(() => !reduceMotion && reviews.value.length > 1)
const marqueeReviews = computed(() =>
  shouldAnimate.value ? [...halfReviews.value, ...halfReviews.value] : reviews.value,
)
// One loop travels half the track: roughly seven seconds per review.
const marqueeDuration = computed(() => `${Math.max(24, halfReviews.value.length * 7)}s`)

function initials(name: string): string {
  return (
    name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('') || 'A'
  )
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    summary.value = await apiFetch<ReviewSummary>('/reviews', { query: { limit: 6 }, auth: false })
  } catch (e) {
    console.error('Could not load reviews', e)
    if (import.meta.env.DEV) {
      if (e instanceof FetchError && e.status === 500) {
        error.value = 'The reviews API returned a server error. If you are running locally, run manage.py migrate.'
      } else if (e instanceof FetchError && e.status === 404) {
        error.value = 'The reviews API route was not found. Restart the API server so it loads the new URL.'
      } else {
        error.value = parseApiError(e).message
      }
    } else {
      error.value = 'Reviews are taking a break right now. Please check back soon.'
    }
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function submit(): Promise<void> {
  submitError.value = ''
  const body = text.value.trim()
  if (body.length < 10) {
    submitError.value = 'Write at least 10 characters.'
    return
  }
  submitting.value = true
  try {
    await apiFetch('/reviews', {
      method: 'POST',
      body: { rating: rating.value, text: body, location: location.value.trim() },
    })
    submitted.value = true
    showForm.value = false
    text.value = ''
    location.value = ''
    rating.value = 5
  } catch (e) {
    const parsed = parseApiError(e)
    submitError.value = parsed.fields.text || parsed.fields.rating || parsed.message
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section id="reviews" aria-labelledby="reviews-title" class="border-t border-line">
    <div class="page-wrap py-10 lg:py-14">
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="text-xs font-bold uppercase tracking-wide text-brand">Reviews</p>
          <h2 id="reviews-title" class="text-2xl font-extrabold sm:text-3xl">What people say about Axora</h2>
          <div v-if="summary && summary.count" class="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted">
            <span class="flex text-brand" role="img" :aria-label="`${summary.average_rating} out of 5 stars`">
              <Star
                v-for="n in 5"
                :key="n"
                class="size-4"
                :fill="n <= averageStars ? 'currentColor' : 'none'"
                :class="n <= averageStars ? '' : 'text-line'"
                aria-hidden="true"
              />
            </span>
            <span>{{ summary.average_rating }} out of 5 · {{ summary.count }} review{{ summary.count === 1 ? '' : 's' }}</span>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <button v-if="auth.isAuthed && !showForm && !submitted" type="button" class="btn btn-outline" @click="showForm = true">
            Write a review
          </button>
          <RouterLink
            v-else-if="!auth.isAuthed"
            :to="{ name: 'login', query: { redirect: '/#reviews' } }"
            class="btn btn-outline"
          >
            Sign in to write a review
          </RouterLink>
          <button
            v-if="shouldAnimate"
            type="button"
            class="btn btn-outline"
            :aria-pressed="paused"
            @click="paused = !paused"
          >
            <Play v-if="paused" class="size-4" aria-hidden="true" />
            <Pause v-else class="size-4" aria-hidden="true" />
            {{ paused ? 'Play reviews' : 'Pause reviews' }}
          </button>
        </div>
      </div>

      <p v-if="loading" class="mt-6 text-muted" role="status">Loading reviews...</p>
      <div v-else-if="error" class="mt-6 rounded-2xl border border-line p-4" role="alert">
        <p class="font-medium text-brand">{{ error }}</p>
        <button type="button" class="btn btn-outline mt-3" @click="load">Try again</button>
      </div>
      <p v-else-if="!reviews.length" class="mt-6 rounded-2xl border border-dashed border-line p-4 text-muted">
        No reviews yet. If Axora helped you find a home, we would love to hear about it.
      </p>
      <div
        v-else
        v-motion
        v-bind="reveal()"
        class="reviews-viewport mt-6"
        :class="{ 'is-static': !shouldAnimate, 'is-paused': paused }"
      >
        <ul class="reviews-track list-none" :style="{ '--reviews-duration': marqueeDuration }">
          <li
            v-for="(review, index) in marqueeReviews"
            :key="`${review.id}-${index}`"
            :aria-hidden="shouldAnimate && index >= reviews.length ? 'true' : undefined"
            class="mr-5 w-80 max-w-[85vw] shrink-0"
          >
            <article class="flex h-full flex-col rounded-2xl border border-line p-5">
              <Quote class="size-7 text-brand" aria-hidden="true" />
              <span class="mt-3 flex text-brand" role="img" :aria-label="`${review.rating} out of 5 stars`">
                <Star
                  v-for="n in 5"
                  :key="n"
                  class="size-4"
                  :fill="n <= review.rating ? 'currentColor' : 'none'"
                  :class="n <= review.rating ? '' : 'text-line'"
                  aria-hidden="true"
                />
              </span>
              <p class="mt-3 flex-1 leading-relaxed">{{ review.text }}</p>
              <div class="mt-4 flex items-center gap-3 border-t border-line pt-4">
                <span class="grid size-10 shrink-0 place-items-center rounded-full bg-brand text-sm font-bold text-white" aria-hidden="true">
                  {{ initials(review.name) }}
                </span>
                <div class="min-w-0">
                  <p class="truncate font-semibold">{{ review.name }}</p>
                  <p v-if="review.location" class="truncate text-sm text-muted">{{ review.location }}</p>
                </div>
              </div>
            </article>
          </li>
        </ul>
      </div>

      <p
        v-if="submitted"
        role="status"
        class="mt-6 flex items-center gap-2 rounded-2xl border border-green-200 bg-green-50 p-4 font-semibold text-green-800"
      >
        <CircleCheck class="size-5 shrink-0" aria-hidden="true" />
        Thank you! Your review will appear here once our team approves it.
      </p>

      <form v-if="showForm" class="mt-6 rounded-2xl border border-line p-5" novalidate @submit.prevent="submit">
        <h3 class="text-xl font-extrabold">Share your experience</h3>
        <p class="mt-1 text-sm text-muted">Your review is checked by our team before it appears.</p>

        <fieldset class="mt-4">
          <legend class="label">Your rating</legend>
          <div class="flex gap-1">
            <label v-for="n in 5" :key="n" class="inline-flex cursor-pointer rounded p-1 focus-within:ring-2 focus-within:ring-brand">
              <input v-model="rating" type="radio" name="review-rating" :value="n" class="sr-only" />
              <Star
                class="size-8"
                :fill="n <= rating ? 'currentColor' : 'none'"
                :class="n <= rating ? 'text-brand' : 'text-line'"
                aria-hidden="true"
              />
              <span class="sr-only">{{ n }} star{{ n === 1 ? '' : 's' }}</span>
            </label>
          </div>
        </fieldset>

        <div class="mt-4">
          <label for="review-location" class="label">
            Your area <span class="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="review-location"
            v-model="location"
            type="text"
            maxlength="80"
            placeholder="e.g. Onitsha, Anambra State"
            class="input"
          />
        </div>

        <div class="mt-4">
          <label for="review-text" class="label">Your review</label>
          <textarea
            id="review-text"
            v-model="text"
            rows="4"
            maxlength="600"
            placeholder="How did Axora help you find a home?"
            class="input"
            :aria-invalid="Boolean(submitError)"
          />
        </div>

        <p v-if="submitError" class="field-error" role="alert">{{ submitError }}</p>

        <div class="mt-4 flex flex-wrap gap-2">
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            {{ submitting ? 'Sending...' : 'Submit review' }}
          </button>
          <button type="button" class="btn btn-outline" @click="showForm = false">Cancel</button>
        </div>
      </form>
    </div>
  </section>
</template>

<style scoped>
.reviews-viewport {
  overflow: hidden;
  -webkit-mask-image: linear-gradient(to right, transparent, black 4%, black 96%, transparent);
  mask-image: linear-gradient(to right, transparent, black 4%, black 96%, transparent);
}

.reviews-track {
  display: flex;
  width: max-content;
  animation: reviews-marquee var(--reviews-duration, 40s) linear infinite;
}

.reviews-viewport:focus-within .reviews-track,
.reviews-viewport.is-paused .reviews-track {
  animation-play-state: paused;
}

@media (hover: hover) {
  .reviews-viewport:hover .reviews-track {
    animation-play-state: paused;
  }
}

.reviews-viewport.is-static {
  overflow-x: auto;
  scroll-snap-type: x proximity;
  -webkit-mask-image: none;
  mask-image: none;
  padding-bottom: 0.5rem;
}

.reviews-viewport.is-static .reviews-track {
  animation: none;
  transform: none;
}

.reviews-viewport.is-static .reviews-track > li {
  scroll-snap-align: start;
}

/* Cards travel from left to right; the two identical halves make the loop seamless. */
@keyframes reviews-marquee {
  from {
    transform: translateX(-50%);
  }
  to {
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .reviews-viewport {
    overflow-x: auto;
    -webkit-mask-image: none;
    mask-image: none;
  }

  .reviews-track {
    animation: none;
    transform: none;
  }
}
</style>

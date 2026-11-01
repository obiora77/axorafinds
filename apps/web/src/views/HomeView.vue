<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import {
  ArrowRight,
  CalendarCheck2,
  ChevronDown,
  CircleCheck,
  Heart,
  MapPin,
  Search,
  ShieldCheck,
  Upload,
  Wallet,
} from 'lucide-vue-next'
import HomeMember from '@/components/HomeMember.vue'
import HomeSearch from '@/components/HomeSearch.vue'
import PropertyCard from '@/components/PropertyCard.vue'
import ReviewsSection from '@/components/ReviewsSection.vue'
import { gridStagger, reveal } from '@/plugins/motion'
import { useAuthStore } from '@/stores/auth'
import { usePropertiesStore } from '@/stores/properties'

const auth = useAuthStore()
const store = usePropertiesStore()

onMounted(() => {
  void store.fetchLatest(8)
})

const trustPoints = [
  'Every listing reviewed by staff',
  'Clear inspection fees before you book',
  'Requests tracked from pending to confirmed',
] as const

const steps = [
  {
    icon: Search,
    title: 'Browse verified homes',
    text: 'Filter by state, city, type, price and bedrooms. Every listing was checked by our team before it went live.',
  },
  {
    icon: CalendarCheck2,
    title: 'Request an inspection',
    text: 'Pick a date and send your contact details. Pay the inspection fee, if there is one, by transfer or in person.',
  },
  {
    icon: ShieldCheck,
    title: 'Get it confirmed',
    text: 'We verify the payment and the listing first, then confirm your visit. No surprises on the day.',
  },
] as const

const features = [
  {
    icon: ShieldCheck,
    title: 'Staff-verified listings',
    text: 'Every home is reviewed before it can appear on Axora, so you spend time on real options.',
  },
  {
    icon: Wallet,
    title: 'No agent fees',
    text: 'Deal with owners and our team, not a chain of agents adding to the cost of moving.',
  },
  {
    icon: Heart,
    title: 'Save and compare',
    text: 'Create a free seeker account and keep the homes you like in one place.',
  },
  {
    icon: Upload,
    title: 'Simple for owners',
    text: 'Add photos and details in minutes and get serious inspection requests, not endless calls.',
  },
] as const

const places: { label: string; note: string; query: Record<string, string> }[] = [
  { label: 'Onitsha', note: 'Anambra State', query: { city: 'Onitsha' } },
  { label: 'Lagos', note: 'Lagos State', query: { state: 'Lagos' } },
  { label: 'Abuja', note: 'FCT', query: { city: 'Abuja' } },
  { label: 'Port Harcourt', note: 'Rivers State', query: { city: 'Port Harcourt' } },
  { label: 'Enugu', note: 'Enugu State', query: { city: 'Enugu' } },
  { label: 'Owerri', note: 'Imo State', query: { city: 'Owerri' } },
]

const faqs = [
  {
    question: 'Are the listings verified?',
    answer:
      'Yes. Owners submit a property and our team reviews it before it is published. Only published listings appear on the site.',
  },
  {
    question: 'What does an inspection cost?',
    answer:
      'Some homes have an inspection fee set by the owner; others have none. The fee is always shown on the listing before you request a visit.',
  },
  {
    question: 'How do I pay an inspection fee?',
    answer:
      'You can choose a bank transfer or pay in person. For transfers, the official account is shown only after you submit the request, and your reference is attached to it.',
  },
  {
    question: 'How long does confirmation take?',
    answer:
      'Our team checks the request and any payment first. You will hear back once the visit is confirmed, and you can contact us in the meantime.',
  },
  {
    question: 'Can I list my property?',
    answer:
      'Yes. Create an owner account, add your photos and details, and send it in. It stays in review until our team publishes it.',
  },
] as const
</script>

<template>
  <div class="pt-3 sm:pt-5">
    <div class="panel">
      <div class="page-wrap py-8 lg:py-12">
        <div v-if="auth.isAuthed" v-motion v-bind="reveal()">
          <HomeMember />
        </div>

        <section v-else v-motion v-bind="reveal()" aria-labelledby="home-title">
          <p class="text-xs font-bold uppercase tracking-wide text-brand">Verified rentals across Nigeria</p>
          <h1 id="home-title" class="mt-2 max-w-3xl text-4xl font-extrabold leading-[1.05] sm:text-5xl">
            Find a verified home without the agent fees.
          </h1>
          <p class="mt-4 max-w-2xl text-lg text-muted">
            Browse homes and land, request an inspection, and let our team check every listing before it goes live.
          </p>
          <HomeSearch class="mt-6" />
          <ul class="mt-5 flex flex-wrap gap-x-5 gap-y-2">
            <li v-for="point in trustPoints" :key="point" class="flex items-center gap-1.5 text-sm font-semibold">
              <CircleCheck class="size-4 shrink-0 text-brand" aria-hidden="true" />
              {{ point }}
            </li>
          </ul>
        </section>

        <div v-if="auth.isAuthed" class="mt-8">
          <h2 class="text-lg font-extrabold">Find your next home</h2>
          <HomeSearch class="mt-3" />
        </div>

        <dl class="mt-8 grid grid-cols-2 gap-3 rounded-2xl bg-[#f8f8fa] p-4 sm:grid-cols-4 sm:p-5">
          <div>
            <dt class="text-sm text-muted">Verified listings</dt>
            <dd class="text-xl font-extrabold sm:text-2xl">{{ store.latestLoading && !store.total ? '...' : store.total }}</dd>
          </div>
          <div>
            <dt class="text-sm text-muted">States supported</dt>
            <dd class="text-xl font-extrabold sm:text-2xl">36 + FCT</dd>
          </div>
          <div>
            <dt class="text-sm text-muted">Agent fees</dt>
            <dd class="text-xl font-extrabold sm:text-2xl">None</dd>
          </div>
          <div>
            <dt class="text-sm text-muted">Listings reviewed</dt>
            <dd class="text-xl font-extrabold sm:text-2xl">Every one</dd>
          </div>
        </dl>
      </div>

      <section class="border-t border-line" aria-labelledby="latest-title">
        <div class="page-wrap py-10 lg:py-14">
          <div v-motion v-bind="reveal()" class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-xs font-bold uppercase tracking-wide text-brand">Fresh on Axora</p>
              <h2 id="latest-title" class="text-2xl font-extrabold sm:text-3xl">Latest verified listings</h2>
            </div>
            <RouterLink to="/properties" class="inline-flex min-h-11 items-center gap-1.5 font-semibold text-brand hover:underline">
              View all properties
              <ArrowRight class="size-4" aria-hidden="true" />
            </RouterLink>
          </div>

          <p v-if="store.latestLoading && !store.latest.length" class="mt-6 text-muted" role="status">Loading listings...</p>
          <p v-else-if="store.latestError" class="mt-6 font-medium text-brand" role="alert">{{ store.latestError }}</p>
          <p v-else-if="!store.latest.length" class="mt-6 text-muted">No listings yet. Check back soon.</p>

          <TransitionGroup
            v-if="store.latest.length"
            tag="ul"
            appear
            :css="false"
            class="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
            @before-enter="gridStagger.onBeforeEnter"
            @enter="gridStagger.onEnter"
            @before-appear="gridStagger.onBeforeEnter"
            @appear="gridStagger.onEnter"
          >
            <li v-for="(property, index) in store.latest" :key="property.id" :data-index="index">
              <PropertyCard :property="property" />
            </li>
          </TransitionGroup>
        </div>
      </section>

      <ReviewsSection />

      <section class="border-t border-line" aria-labelledby="how-title">
        <div class="page-wrap py-10 lg:py-14">
          <div v-motion v-bind="reveal()" class="max-w-2xl">
            <p class="text-xs font-bold uppercase tracking-wide text-brand">How it works</p>
            <h2 id="how-title" class="text-2xl font-extrabold sm:text-3xl">From search to keys in three steps</h2>
            <p class="mt-2 text-muted">A short, clear process with a real person checking each step.</p>
          </div>

          <ol class="mt-8 grid gap-5 md:grid-cols-3">
            <li
              v-for="(step, index) in steps"
              :key="step.title"
              v-motion
              v-bind="reveal(index * 60)"
              class="rounded-2xl border border-line p-5"
            >
              <div class="flex items-center gap-3">
                <span class="grid size-11 shrink-0 place-items-center rounded-full bg-brand text-white">
                  <component :is="step.icon" class="size-5" aria-hidden="true" />
                </span>
                <span class="text-xs font-bold uppercase tracking-wide text-muted">Step {{ index + 1 }}</span>
              </div>
              <h3 class="mt-4 text-lg font-bold">{{ step.title }}</h3>
              <p class="mt-1 text-muted">{{ step.text }}</p>
            </li>
          </ol>
        </div>
      </section>

      <section class="border-t border-line bg-[#fafafa]" aria-labelledby="why-title">
        <div class="page-wrap py-10 lg:py-14">
          <div v-motion v-bind="reveal()" class="max-w-2xl">
            <p class="text-xs font-bold uppercase tracking-wide text-brand">Why Axora</p>
            <h2 id="why-title" class="text-2xl font-extrabold sm:text-3xl">Built to take the stress out of renting</h2>
            <p class="mt-2 text-muted">Less guessing, fewer middlemen and a record of every request.</p>
          </div>

          <ul class="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <li
              v-for="(feature, index) in features"
              :key="feature.title"
              v-motion
              v-bind="reveal(index * 50)"
              class="rounded-2xl border border-line bg-white p-5"
            >
              <component :is="feature.icon" class="size-7 text-brand" aria-hidden="true" />
              <h3 class="mt-3 text-lg font-bold">{{ feature.title }}</h3>
              <p class="mt-1 text-sm text-muted">{{ feature.text }}</p>
            </li>
          </ul>
        </div>
      </section>

      <section class="border-t border-line" aria-labelledby="places-title">
        <div class="page-wrap py-10 lg:py-14">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-xs font-bold uppercase tracking-wide text-brand">Places</p>
              <h2 id="places-title" class="text-2xl font-extrabold sm:text-3xl">Popular places to look</h2>
            </div>
            <RouterLink to="/properties" class="inline-flex min-h-11 items-center gap-1.5 font-semibold text-brand hover:underline">
              See all properties
              <ArrowRight class="size-4" aria-hidden="true" />
            </RouterLink>
          </div>

          <ul class="mt-6 flex flex-wrap gap-3">
            <li v-for="place in places" :key="place.label">
              <RouterLink
                :to="{ name: 'properties', query: place.query }"
                class="group flex min-h-11 items-center gap-2 rounded-full border border-line px-4 py-2 font-semibold transition-colors duration-200 ease-out hover:border-brand hover:text-brand"
              >
                <MapPin class="size-4 shrink-0 text-brand" aria-hidden="true" />
                {{ place.label }}
                <span class="text-sm font-normal text-muted group-hover:text-brand">{{ place.note }}</span>
                <ArrowRight class="size-4 shrink-0 text-muted group-hover:text-brand" aria-hidden="true" />
              </RouterLink>
            </li>
          </ul>
        </div>
      </section>

      <section class="border-t border-line" aria-labelledby="faq-title">
        <div class="page-wrap py-10 lg:py-14">
          <div class="max-w-2xl">
            <p class="text-xs font-bold uppercase tracking-wide text-brand">Good to know</p>
            <h2 id="faq-title" class="text-2xl font-extrabold sm:text-3xl">Questions people ask</h2>
          </div>

          <div class="mt-6 max-w-3xl divide-y divide-line border-y border-line">
            <details v-for="faq in faqs" :key="faq.question" class="group py-4">
              <summary
                class="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold [&::-webkit-details-marker]:hidden"
              >
                {{ faq.question }}
                <ChevronDown
                  class="size-5 shrink-0 text-brand transition-transform duration-200 ease-out group-open:rotate-180"
                  aria-hidden="true"
                />
              </summary>
              <p class="mt-2 text-muted">{{ faq.answer }}</p>
            </details>
          </div>

          <p class="mt-6 text-muted">
            Still have a question?
            <RouterLink to="/contact" class="font-semibold text-brand hover:underline">Talk to our team</RouterLink>.
          </p>
        </div>
      </section>
    </div>

    <section class="on-red text-white" aria-labelledby="home-cta-title">
      <div class="page-wrap py-12 text-center lg:py-16">
        <h2 id="home-cta-title" class="text-3xl font-extrabold sm:text-4xl">Ready for a simpler house hunt?</h2>
        <p class="mx-auto mt-3 max-w-xl text-lg">
          Browse verified homes, book an inspection and let our team handle the checks.
        </p>
        <div class="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
          <RouterLink to="/properties" class="btn btn-light px-8">Browse properties</RouterLink>
          <RouterLink
            v-if="auth.isOwner"
            to="/list-property"
            class="btn border border-white bg-transparent text-white hover:bg-white hover:text-brand"
          >
            List your property
          </RouterLink>
          <RouterLink
            v-else-if="!auth.isAuthed"
            to="/signup"
            class="btn border border-white bg-transparent text-white hover:bg-white hover:text-brand"
          >
            Create an account
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

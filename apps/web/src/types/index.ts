export type Role = 'seeker' | 'owner' | 'staff'

export interface User {
  id: number
  email: string
  name: string
  phone: string
  role: Role
  /** True for role "staff" and for Django superusers created with createsuperuser. */
  is_staff: boolean
}

export interface AuthResponse {
  access: string
  refresh: string
  user: User
}

export type PropertyType = 'room_parlour' | 'self_contain' | 'flat' | 'duplex' | 'bungalow' | 'land'

export interface PropertyCardData {
  id: number
  slug: string
  title: string
  /** Decimal string in NGN, e.g. "300000.00". */
  price: string
  state: string
  city: string
  /** Ready-made label, e.g. "Onitsha, Anambra State". */
  location: string
  bedrooms: number
  property_type: PropertyType
  /** Short label, e.g. "2 Rooms and parlour". */
  short_type: string
  cover: string | null
}

export interface Photo {
  id: number
  url: string
}

export interface PropertyDetailData extends PropertyCardData {
  bathrooms: number
  address: string
  description: string
  amenities: string[]
  inspection_fee: string
  status: 'pending' | 'published' | 'rejected'
  photos: Photo[]
}

export interface Paged<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Review {
  id: number
  name: string
  location: string
  rating: number
  text: string
  created_at: string
}

export interface ReviewSummary {
  count: number
  average_rating: number | null
  results: Review[]
}

export interface PropertyFilters {
  q?: string
  state?: string
  city?: string
  type?: string
  max_price?: string
  bedrooms?: string
}

export type PaymentChoice = 'transfer' | 'in_person'

export interface InspectionResult {
  id: number
  reference: string
  name: string
  phone: string
  email: string
  property: number
  date: string
  note: string
  payment_choice: PaymentChoice
  fee_amount: string
  payment_status: 'not_required' | 'unpaid' | 'verified'
  status: 'pending' | 'confirmed' | 'rejected'
  /** Present only for bank-transfer requests; needed to fetch the account. */
  payment_token?: string
}

export interface PaymentAccount {
  reference: string
  amount: string
  bank_name: string
  account_name: string
  account_number: string
  note: string
}

// --- Staff dashboard (/api/staff) ------------------------------------------

export type ListingStatus = 'pending' | 'published' | 'rejected'

export interface StaffEmailStatus {
  enabled: boolean
  backend: string
  host: string | null
  port: number | null
  use_tls: boolean
  use_ssl: boolean
  from_email: string
  team_email: string
  site_url: string
  last_error: string | null
  templates_ready: boolean
  missing_templates: string[]
  message_count: number
}

export interface StaffListing {
  id: number
  slug: string
  title: string
  property_type: PropertyType
  short_type: string
  price: string
  state: string
  city: string
  location: string
  bedrooms: number
  bathrooms: number
  inspection_fee: string
  status: ListingStatus
  cover: string | null
  photos_count: number
  owner_name: string
  owner_email: string
  created_at: string
  published_at: string | null
  reviewed_at: string | null
}

export interface StaffInspection {
  id: number
  reference: string
  name: string
  phone: string
  email: string
  property: number
  property_title: string
  property_slug: string
  preferred_date: string
  note: string
  payment_choice: PaymentChoice
  payment_choice_display: string
  fee_amount: string
  payment_status: 'not_required' | 'unpaid' | 'verified'
  payment_status_display: string
  status: 'pending' | 'confirmed' | 'rejected'
  status_display: string
  staff_note: string
  created_at: string
  decided_at: string | null
  can_verify_payment: boolean
  can_confirm: boolean
  can_reject: boolean
}

export interface StaffReview {
  id: number
  name: string
  location: string
  rating: number
  text: string
  is_published: boolean
  author_email: string | null
  created_at: string
}

export interface StaffContactMessage {
  id: number
  name: string
  email: string
  message: string
  created_at: string
}

export interface StaffSubscriber {
  id: number
  email: string
  created_at: string
}

export interface StaffUser {
  id: number
  email: string
  name: string
  phone: string
  role: Role
  is_active: boolean
  is_staff: boolean
  date_joined: string
  last_login: string | null
}

export interface StaffSiteSettings {
  bank_name: string
  account_name: string
  account_number: string
  transfer_note: string
  is_live: boolean
  has_account: boolean
}

export interface StaffCounts {
  listings: { total: number; pending: number; published: number; rejected: number }
  inspections: {
    total: number
    pending: number
    confirmed: number
    rejected: number
    awaiting_payment: number
    ready_to_confirm: number
  }
  reviews: { total: number; pending: number; published: number }
  contacts: number
  subscribers: number
  users: { total: number; active: number }
}

export interface StaffOverview {
  counts: StaffCounts
  recent: {
    listings: StaffListing[]
    inspections: StaffInspection[]
    reviews: StaffReview[]
  }
  email: StaffEmailStatus
}

export interface StaffActionResult {
  email_sent: boolean
  email_error: string | null
  email_note: string | null
}

export interface EmailTestResult {
  sent: boolean
  to: string
  error: string | null
  status: StaffEmailStatus
}

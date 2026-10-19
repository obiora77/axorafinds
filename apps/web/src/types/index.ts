export type Role = 'seeker' | 'owner' | 'staff'

export interface User {
  id: number
  email: string
  name: string
  phone: string
  role: Role
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

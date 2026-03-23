export type GeocodingStatus = 'verified' | 'ambiguous' | 'failed'

export interface Event {
  id: string
  title: string
  venueName: string
  venueId: string
  thumbnail?: string
  image?: string
  geocodingStatus: GeocodingStatus
  category: string
  location: string
  startTime: string
  endTime: string
  hypeScore: number
  ticketUrl?: string
  additionalDates?: string[]
  sourceUrl: string
  latitude: number
  longitude: number
}

export interface Venue {
  id: string
  title: string
  city: string
  address: string
  latitude: number
  longitude: number
  isVerified: boolean
  relevance: number
  linkedEventIds: string[]
}

export interface LocationSuggestion {
  id: string
  placeName: string
  address: string
  latitude: number
  longitude: number
}

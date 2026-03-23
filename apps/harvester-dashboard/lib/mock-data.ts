import type { Event, Venue, LocationSuggestion } from './types'

export const mockEvents: Event[] = [
  {
    id: 'evt-1',
    title: 'Tech Summit 2026',
    venueName: 'Moscone Center',
    venueId: 'ven-1',
    thumbnail: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=400&h=300&fit=crop',
    image: 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&h=500&fit=crop',
    geocodingStatus: 'verified',
    category: 'Technology',
    location: 'San Francisco, CA',
    startTime: '2026-04-15T09:00:00',
    endTime: '2026-04-15T18:00:00',
    hypeScore: 92,
    ticketUrl: 'https://example.com/tickets/tech-summit',
    additionalDates: ['2026-04-16', '2026-04-17'],
    sourceUrl: 'https://example.com/source/tech-summit',
    latitude: 37.7849,
    longitude: -122.4006
  },
  {
    id: 'evt-2',
    title: 'Jazz Night Live',
    venueName: 'Blue Note NYC',
    venueId: 'ven-2',
    thumbnail: 'https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=400&h=300&fit=crop',
    image: 'https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?w=800&h=500&fit=crop',
    geocodingStatus: 'verified',
    category: 'Music',
    location: 'New York, NY',
    startTime: '2026-03-28T20:00:00',
    endTime: '2026-03-28T23:30:00',
    hypeScore: 78,
    ticketUrl: 'https://example.com/tickets/jazz-night',
    sourceUrl: 'https://example.com/source/jazz-night',
    latitude: 40.7308,
    longitude: -74.0012
  },
  {
    id: 'evt-3',
    title: 'Outdoor Food Festival',
    venueName: 'Central Park',
    venueId: 'ven-3',
    thumbnail: 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=400&h=300&fit=crop',
    image: 'https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=800&h=500&fit=crop',
    geocodingStatus: 'ambiguous',
    category: 'Food & Drink',
    location: 'New York, NY',
    startTime: '2026-05-01T11:00:00',
    endTime: '2026-05-01T21:00:00',
    hypeScore: 85,
    ticketUrl: 'https://example.com/tickets/food-fest',
    sourceUrl: 'https://example.com/source/food-fest',
    latitude: 40.7829,
    longitude: -73.9654
  },
  {
    id: 'evt-4',
    title: 'Startup Pitch Night',
    venueName: 'WeWork Embarcadero',
    venueId: 'ven-4',
    geocodingStatus: 'failed',
    category: 'Business',
    location: 'San Francisco, CA',
    startTime: '2026-04-02T18:00:00',
    endTime: '2026-04-02T21:00:00',
    hypeScore: 65,
    sourceUrl: 'https://example.com/source/pitch-night',
    latitude: 37.7932,
    longitude: -122.3959
  },
  {
    id: 'evt-5',
    title: 'Modern Art Exhibition',
    venueName: 'SFMOMA',
    venueId: 'ven-5',
    thumbnail: 'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=400&h=300&fit=crop',
    image: 'https://images.unsplash.com/photo-1531243269054-5ebf6f34081e?w=800&h=500&fit=crop',
    geocodingStatus: 'verified',
    category: 'Art',
    location: 'San Francisco, CA',
    startTime: '2026-03-20T10:00:00',
    endTime: '2026-06-20T17:00:00',
    hypeScore: 88,
    ticketUrl: 'https://example.com/tickets/art-exhibit',
    sourceUrl: 'https://example.com/source/art-exhibit',
    latitude: 37.7857,
    longitude: -122.4011
  },
  {
    id: 'evt-6',
    title: 'Yoga Sunrise Session',
    venueName: 'Golden Gate Park',
    venueId: 'ven-6',
    thumbnail: 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400&h=300&fit=crop',
    image: 'https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&h=500&fit=crop',
    geocodingStatus: 'ambiguous',
    category: 'Health & Wellness',
    location: 'San Francisco, CA',
    startTime: '2026-04-05T06:00:00',
    endTime: '2026-04-05T07:30:00',
    hypeScore: 72,
    sourceUrl: 'https://example.com/source/yoga',
    latitude: 37.7694,
    longitude: -122.4862
  },
  {
    id: 'evt-7',
    title: 'Comedy Stand-up Night',
    venueName: 'The Comedy Store',
    venueId: 'ven-7',
    thumbnail: 'https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=400&h=300&fit=crop',
    image: 'https://images.unsplash.com/photo-1527224857830-43a7acc85260?w=800&h=500&fit=crop',
    geocodingStatus: 'verified',
    category: 'Comedy',
    location: 'Los Angeles, CA',
    startTime: '2026-04-10T21:00:00',
    endTime: '2026-04-10T23:30:00',
    hypeScore: 81,
    ticketUrl: 'https://example.com/tickets/comedy',
    sourceUrl: 'https://example.com/source/comedy',
    latitude: 34.0906,
    longitude: -118.3868
  },
  {
    id: 'evt-8',
    title: 'Blockchain Conference',
    venueName: 'Miami Beach Convention',
    venueId: 'ven-8',
    thumbnail: 'https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=400&h=300&fit=crop',
    image: 'https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=800&h=500&fit=crop',
    geocodingStatus: 'failed',
    category: 'Technology',
    location: 'Miami, FL',
    startTime: '2026-05-15T08:00:00',
    endTime: '2026-05-17T18:00:00',
    hypeScore: 95,
    ticketUrl: 'https://example.com/tickets/blockchain',
    additionalDates: ['2026-05-16', '2026-05-17'],
    sourceUrl: 'https://example.com/source/blockchain',
    latitude: 25.7907,
    longitude: -80.1300
  }
]

export const mockVenues: Venue[] = [
  {
    id: 'ven-1',
    title: 'Moscone Center',
    city: 'San Francisco',
    address: '747 Howard St, San Francisco, CA 94103',
    latitude: 37.7849,
    longitude: -122.4006,
    isVerified: true,
    relevance: 95,
    linkedEventIds: ['evt-1']
  },
  {
    id: 'ven-2',
    title: 'Blue Note NYC',
    city: 'New York',
    address: '131 W 3rd St, New York, NY 10012',
    latitude: 40.7308,
    longitude: -74.0012,
    isVerified: true,
    relevance: 88,
    linkedEventIds: ['evt-2']
  },
  {
    id: 'ven-3',
    title: 'Central Park',
    city: 'New York',
    address: 'Central Park, New York, NY',
    latitude: 40.7829,
    longitude: -73.9654,
    isVerified: false,
    relevance: 75,
    linkedEventIds: ['evt-3']
  },
  {
    id: 'ven-4',
    title: 'WeWork Embarcadero',
    city: 'San Francisco',
    address: '2 Embarcadero Center, San Francisco, CA 94111',
    latitude: 37.7932,
    longitude: -122.3959,
    isVerified: false,
    relevance: 60,
    linkedEventIds: ['evt-4']
  },
  {
    id: 'ven-5',
    title: 'SFMOMA',
    city: 'San Francisco',
    address: '151 3rd St, San Francisco, CA 94103',
    latitude: 37.7857,
    longitude: -122.4011,
    isVerified: true,
    relevance: 92,
    linkedEventIds: ['evt-5']
  },
  {
    id: 'ven-6',
    title: 'Golden Gate Park',
    city: 'San Francisco',
    address: 'Golden Gate Park, San Francisco, CA',
    latitude: 37.7694,
    longitude: -122.4862,
    isVerified: false,
    relevance: 70,
    linkedEventIds: ['evt-6']
  },
  {
    id: 'ven-7',
    title: 'The Comedy Store',
    city: 'Los Angeles',
    address: '8433 Sunset Blvd, Los Angeles, CA 90069',
    latitude: 34.0906,
    longitude: -118.3868,
    isVerified: true,
    relevance: 85,
    linkedEventIds: ['evt-7']
  },
  {
    id: 'ven-8',
    title: 'Miami Beach Convention',
    city: 'Miami',
    address: '1901 Convention Center Dr, Miami Beach, FL 33139',
    latitude: 25.7907,
    longitude: -80.1300,
    isVerified: false,
    relevance: 78,
    linkedEventIds: ['evt-8']
  }
]

export const mockLocationSuggestions: LocationSuggestion[] = [
  {
    id: 'loc-1',
    placeName: 'Moscone Center',
    address: '747 Howard St, San Francisco, CA 94103',
    latitude: 37.7849,
    longitude: -122.4006
  },
  {
    id: 'loc-2',
    placeName: 'Moscone West',
    address: '800 Howard St, San Francisco, CA 94103',
    latitude: 37.7838,
    longitude: -122.4032
  },
  {
    id: 'loc-3',
    placeName: 'Moscone South',
    address: '747 Howard St, San Francisco, CA 94103',
    latitude: 37.7835,
    longitude: -122.4001
  }
]

export const categories = [
  'All Categories',
  'Technology',
  'Music',
  'Food & Drink',
  'Business',
  'Art',
  'Health & Wellness',
  'Comedy',
  'Sports',
  'Education'
]

export const locations = [
  'All Locations',
  'San Francisco, CA',
  'New York, NY',
  'Los Angeles, CA',
  'Miami, FL',
  'Chicago, IL',
  'Austin, TX'
]

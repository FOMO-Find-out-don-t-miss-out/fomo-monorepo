import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import type { PendingEvent, Venue } from '@/types/api'

// ── Next.js shims ────────────────────────────────────────────────────────────
vi.mock('next/image', () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}))
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}))
vi.mock('next/navigation', () => ({
  useRouter: vi.fn(() => ({ replace: vi.fn() })),
  usePathname: vi.fn(() => '/'),
}))

// ── TanStack Query ───────────────────────────────────────────────────────────
vi.mock('@tanstack/react-query', () => ({
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useQuery: vi.fn(() => ({ data: [], isLoading: false })),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}))

// ── API client ───────────────────────────────────────────────────────────────
vi.mock('@/lib/api', () => ({
  moderationApi: {
    getMapboxSuggestions: vi.fn(() => Promise.resolve([])),
    getVenues: vi.fn(() => Promise.resolve([])),
    getPendingEvents: vi.fn(() => Promise.resolve([])),
    getPublishedEvents: vi.fn(() => Promise.resolve([])),
  },
}))

// ── Sonner toast ─────────────────────────────────────────────────────────────
vi.mock('sonner', () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }))

// ── date-fns (format used inside components) ─────────────────────────────────
vi.mock('date-fns', () => ({
  format: vi.fn(() => '01 Jul 2026'),
}))

import { EventInspector } from '../event-inspector'
import { VenueInspector } from '../venue-inspector'

// ── Minimal fixtures ──────────────────────────────────────────────────────────

const BASE_EVENT: PendingEvent = {
  id: 'evt-1',
  title: 'Test Event',
  location: null,
  location_name: 'Test Venue',
  start_time: '2026-07-01T20:00:00Z',
  end_time: '2026-07-01T23:00:00Z',
  category: 'Music',
  sub_category: null,
  status: 'pending',
  geocoding_status: 'ambiguous',
  geocoding_metadata: {},
  confidence_score: 0.5,
  hype_score: 50,
  ticket_url: null,
  source_url: null,
  source_provider: 'test',
  ingestion_method: 'json_ld',
  photo_url: null,
  event_metadata: {},
  tags: [],
  country_code: 'GR',
}

const BASE_VENUE: Venue = {
  id: 'venue-1',
  name: 'Test Venue',
  city: 'Athens',
  country_code: 'GR',
  lat: 37.9838,
  lng: 23.7275,
  full_address: 'Test Street 1, Athens',
  relevance: 0.9,
  verification_status: 'unverified',
  created_at: '2026-06-01T00:00:00Z',
}

const UNRESOLVED_VENUE: Venue = {
  ...BASE_VENUE,
  lat: null,
  lng: null,
  full_address: null,
}

const noop = vi.fn()

// ── Helper: render EventInspector with a token env override ──────────────────

function renderEventInspector(token: string | undefined) {
  if (token !== undefined) {
    vi.stubEnv('NEXT_PUBLIC_MAPBOX_TOKEN', token)
  } else {
    vi.unstubAllEnvs()
  }
  return render(
    <EventInspector
      event={BASE_EVENT}
      open
      onOpenChange={noop}
      onApprove={noop}
      onReject={noop}
    />,
  )
}

function renderVenueInspector(token: string | undefined, venue = BASE_VENUE) {
  if (token !== undefined) {
    vi.stubEnv('NEXT_PUBLIC_MAPBOX_TOKEN', token)
  } else {
    vi.unstubAllEnvs()
  }
  return render(
    <VenueInspector venue={venue} open onOpenChange={noop} />,
  )
}

afterEach(() => {
  vi.unstubAllEnvs()
})

// ── EventInspector map guard tests ───────────────────────────────────────────

describe('EventInspector — Mapbox token guard', () => {
  it('renders fallback when NEXT_PUBLIC_MAPBOX_TOKEN is not set', () => {
    renderEventInspector(undefined)

    expect(screen.queryByTitle('Event Location')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Map is unavailable because the Mapbox public token is not configured correctly.',
      ),
    ).toBeInTheDocument()
  })

  it('renders fallback when token starts with sk.', () => {
    renderEventInspector('sk.eyJhbGciOiJIUzI1NiJ9.secret')

    expect(screen.queryByTitle('Event Location')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Map is unavailable because the Mapbox public token is not configured correctly.',
      ),
    ).toBeInTheDocument()
  })

  it('renders the map iframe when token starts with pk.', () => {
    renderEventInspector('pk.eyJhbGciOiJIUzI1NiJ9.public')

    const iframe = screen.getByTitle('Event Location')
    expect(iframe).toBeInTheDocument()
    expect((iframe as HTMLIFrameElement).src).toContain('pk.eyJhbGciOiJIUzI1NiJ9.public')
    expect((iframe as HTMLIFrameElement).src).not.toContain('sk.')
  })

  it('does not include sk. token in the iframe src', () => {
    renderEventInspector('sk.leaked.token')

    expect(screen.queryByTitle('Event Location')).not.toBeInTheDocument()
  })
})

// ── VenueInspector map guard tests ───────────────────────────────────────────

describe('VenueInspector — Mapbox token guard', () => {
  it('renders fallback when NEXT_PUBLIC_MAPBOX_TOKEN is not set', () => {
    renderVenueInspector(undefined)

    expect(screen.queryByTitle('Venue Location')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Map is unavailable because the Mapbox public token is not configured correctly.',
      ),
    ).toBeInTheDocument()
  })

  it('renders fallback when token starts with sk.', () => {
    renderVenueInspector('sk.eyJhbGciOiJIUzI1NiJ9.secret')

    expect(screen.queryByTitle('Venue Location')).not.toBeInTheDocument()
    expect(
      screen.getByText(
        'Map is unavailable because the Mapbox public token is not configured correctly.',
      ),
    ).toBeInTheDocument()
  })

  it('renders the map iframe when token starts with pk. and coords exist', () => {
    renderVenueInspector('pk.eyJhbGciOiJIUzI1NiJ9.public')

    const iframe = screen.getByTitle('Venue Location')
    expect(iframe).toBeInTheDocument()
    expect((iframe as HTMLIFrameElement).src).toContain('pk.eyJhbGciOiJIUzI1NiJ9.public')
  })

  it('renders geocoding-pending message when venue has no coordinates', () => {
    renderVenueInspector('pk.eyJhbGciOiJIUzI1NiJ9.public', UNRESOLVED_VENUE)

    expect(screen.queryByTitle('Venue Location')).not.toBeInTheDocument()
    expect(
      screen.getByText('Location not yet resolved — geocoding pending'),
    ).toBeInTheDocument()
  })
})

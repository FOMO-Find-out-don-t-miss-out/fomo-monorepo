import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import type { PendingEvent } from '@/types/api'

// ── Next.js shims ────────────────────────────────────────────────────────────
vi.mock('next/image', () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
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
    updateEvent: vi.fn(),
    updatePublishedEvent: vi.fn(),
  },
}))

// ── Sonner toast ─────────────────────────────────────────────────────────────
vi.mock('sonner', () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }))

// ── date-fns (format used inside components) ─────────────────────────────────
vi.mock('date-fns', () => ({
  format: vi.fn(() => '01 Jul 2026'),
}))

import { EventInspector } from '../event-inspector'
import { EventList } from '../event-list'
import { FilterSidebar } from '../filter-sidebar'
import { dedupeStatusLabel } from '@/lib/utils'

const noop = vi.fn()

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
  dedupe_status: 'not_checked',
  candidate_event_id: null,
}

const PUBLISHED_EVENT: PendingEvent = { ...BASE_EVENT, id: 'evt-2', status: 'published' }

describe('EventInspector — mode-aware actions', () => {
  it('shows Approve and Reject in pending mode', () => {
    render(
      <EventInspector
        mode="pending"
        event={BASE_EVENT}
        open
        onOpenChange={noop}
        onApprove={noop}
        onReject={noop}
      />,
    )

    expect(screen.getByText('Approve')).toBeInTheDocument()
    expect(screen.getByText('Reject')).toBeInTheDocument()
  })

  it('does not show Approve or Reject in published mode, only Unpublish', () => {
    render(
      <EventInspector
        mode="published"
        event={PUBLISHED_EVENT}
        open
        onOpenChange={noop}
        onApprove={noop}
        onReject={noop}
      />,
    )

    expect(screen.queryByText('Approve')).not.toBeInTheDocument()
    expect(screen.queryByText('Reject')).not.toBeInTheDocument()
    expect(screen.getByText('Unpublish Event')).toBeInTheDocument()
  })
})

describe('EventList — mode-aware bulk actions and selection', () => {
  const listProps = {
    events: [BASE_EVENT],
    selectedEvent: null,
    selectedEventIds: [BASE_EVENT.id],
    searchQuery: '',
    onSearchChange: noop,
    onSelectEvent: noop,
    onToggleEventCheck: noop,
    onSelectAll: noop,
    onBulkApprove: noop,
    onBulkReject: noop,
  }

  it('shows bulk Execute/Abort actions in pending mode when items are selected', () => {
    render(<EventList mode="pending" {...listProps} />)

    expect(screen.getByText(/Execute/)).toBeInTheDocument()
    expect(screen.getByText('Abort')).toBeInTheDocument()
  })

  it('does not show bulk Execute/Abort actions in published mode', () => {
    render(<EventList mode="published" {...listProps} />)

    expect(screen.queryByText(/Execute/)).not.toBeInTheDocument()
    expect(screen.queryByText('Abort')).not.toBeInTheDocument()
  })
})

describe('FilterSidebar — Collision Status filter', () => {
  const baseProps = {
    selectedCategory: 'All Categories',
    setSelectedCategory: noop,
    selectedStatus: 'all' as const,
    setSelectedStatus: noop,
    selectedSource: 'all' as const,
    setSelectedSource: noop,
    eventCounts: { verified: 0, ambiguous: 0, failed: 0, total: 0 },
  }

  it('renders the Collision Status filter in pending mode', () => {
    render(
      <FilterSidebar
        mode="pending"
        {...baseProps}
        selectedDedupeStatus="all"
        setSelectedDedupeStatus={noop}
        dedupeCounts={{ not_checked: 0, duplicate_confirmed: 0, possible_match: 0, total: 0 }}
      />,
    )

    expect(screen.getByText('Collision Status')).toBeInTheDocument()
  })

  it('does not render the Collision Status filter without dedupe props (e.g. published mode)', () => {
    render(<FilterSidebar mode="published" {...baseProps} />)

    expect(screen.queryByText('Collision Status')).not.toBeInTheDocument()
  })
})

describe('dedupeStatusLabel', () => {
  it('renders readable labels for known dedupe statuses', () => {
    expect(dedupeStatusLabel('not_checked')).toBe('Not checked')
    expect(dedupeStatusLabel('possible_match')).toBe('Possible match')
    expect(dedupeStatusLabel('duplicate_confirmed')).toBe('Duplicate confirmed')
  })

  it('falls back to a readable label for unknown values', () => {
    expect(dedupeStatusLabel('some_new_status')).toBe('Some New Status')
  })
})

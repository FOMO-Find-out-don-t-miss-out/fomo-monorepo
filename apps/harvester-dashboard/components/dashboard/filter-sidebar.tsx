'use client'

import { useState, useEffect } from 'react'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'
import { CheckCircle2, AlertCircle, XCircle, Filter, Search, MapPin, Database, Copy, ShieldQuestion } from 'lucide-react'
import { moderationApi } from '@/lib/api'
import type { GeocodeSuggestion } from '@/types/api'
import { cn, categoryLabel, EVENT_CATEGORIES } from '@/lib/utils'

interface FilterSidebarProps {
  mode: 'pending' | 'published'
  selectedCategory: string
  setSelectedCategory: (category: string) => void
  selectedStatus: string | 'all'
  setSelectedStatus: (status: string | 'all') => void
  selectedSource: string | 'all'
  setSelectedSource: (source: string | 'all') => void
  selectedDedupeStatus?: string | 'all'
  setSelectedDedupeStatus?: (status: string | 'all') => void
  /** total reflects only the currently loaded result set, not a global DB count. */
  eventCounts: {
    total: number
  }
  /** Presence (not contents) of this object gates whether the Collision Status filter renders. */
  dedupeCounts?: {
    total: number
  }
  onSuggestionSelect?: (suggestion: GeocodeSuggestion) => void
}

// FOMO-166: filter values are the canonical backend EventCategory values, not
// display labels — see categoryLabel() for the friendly text shown in the UI.
const categories = ['All Categories', ...EVENT_CATEGORIES]
const sources = ['all', 'more.com', 'ticketmaster.com', 'manual', 'unknown']

export function FilterSidebar({
  mode,
  selectedCategory,
  setSelectedCategory,
  selectedStatus,
  setSelectedStatus,
  selectedSource,
  setSelectedSource,
  selectedDedupeStatus = 'all',
  setSelectedDedupeStatus,
  eventCounts,
  dedupeCounts,
  onSuggestionSelect
}: FilterSidebarProps) {
  const [locationSearch, setLocationSearch] = useState('')
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (locationSearch.length > 2) {
        try {
          const res = await moderationApi.getMapboxSuggestions(locationSearch)
          setSuggestions(res)
        } catch (err) {
          console.error('Failed to fetch suggestions', err)
        }
      } else {
        setSuggestions([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [locationSearch])

  return (
    <aside className="w-72 flex-shrink-0 border-r border-neon-blue/10 bg-card/40 backdrop-blur-xl flex flex-col min-h-0 z-10">
      <div className="p-6 border-b border-neon-blue/10 bg-card/20">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-8 h-8 rounded-lg bg-neon-purple/20 flex items-center justify-center border border-neon-purple/30">
            <Filter className="w-4 h-4 text-neon-purple" />
          </div>
          <h2 className="font-black text-foreground uppercase tracking-tighter text-sm italic">
            {mode === 'pending' ? 'Moderation Control' : 'Signal Archive'}
          </h2>
        </div>
        <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-neon-blue animate-neon-pulse shadow-[0_0_5px_var(--neon-blue)]" />
            <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em]" title="Count reflects the currently loaded result set, not the total in the database">
                Showing {eventCounts.total} loaded signals
            </p>
        </div>
      </div>

      <ScrollArea className="flex-1 min-h-0 scrollbar-neon">
        <div className="p-6 space-y-8">
          {/* Quick Location Search - Only for Pending */}
          {mode === 'pending' && (
            <div className="space-y-3">
              <Label className="text-[10px] font-black text-neon-blue uppercase tracking-[0.2em] ml-1 flex items-center gap-2">
                <MapPin className="w-3.5 h-3.5" />
                Registry Trace
              </Label>
              <div className="relative group">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-neon-blue transition-colors" />
                <Input
                  placeholder="Find address..."
                  value={locationSearch}
                  onChange={(e) => setLocationSearch(e.target.value)}
                  className="pl-9 h-9 text-xs bg-card/60 input-neon font-medium"
                />
              </div>
              {suggestions.length > 0 && (
                <div className="mt-2 border border-neon-blue/20 rounded-xl overflow-hidden bg-card/90 backdrop-blur-md shadow-2xl z-50 max-h-56 overflow-y-auto animate-in fade-in slide-in-from-top-2 duration-200">
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      className="w-full p-3 text-left hover:bg-neon-blue/10 transition-all border-b border-neon-blue/10 last:border-b-0 group"
                      onClick={() => {
                        onSuggestionSelect?.(s)
                        setLocationSearch('')
                        setSuggestions([])
                      }}
                    >
                      <div className="font-bold text-[11px] text-foreground group-hover:text-neon-blue transition-colors truncate">{s.full_address}</div>
                      <div className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mt-0.5 truncate">{s.city}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Category Filter */}
          <div className="space-y-3">
            <Label className="text-[10px] font-black text-neon-purple uppercase tracking-[0.2em] ml-1">
              Category Matrix
            </Label>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger className="w-full h-10 bg-card/40 input-neon font-bold uppercase tracking-widest text-[10px]">
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent className="bg-card border-neon-purple/20">
                {categories.map((category) => (
                  <SelectItem key={category} value={category} className="text-[10px] font-bold uppercase tracking-widest">
                    {category === 'All Categories' ? category : categoryLabel(category)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Source Filter */}
          <div className="space-y-3">
            <Label className="text-[10px] font-black text-neon-blue uppercase tracking-[0.2em] ml-1 flex items-center gap-2">
              <Database className="w-3.5 h-3.5" />
              Ingestion Source
            </Label>
            <Select value={selectedSource} onValueChange={setSelectedSource}>
              <SelectTrigger className="w-full h-10 bg-card/40 input-neon font-bold uppercase tracking-widest text-[10px]">
                <SelectValue placeholder="All Sources" />
              </SelectTrigger>
              <SelectContent className="bg-card border-neon-blue/20">
                {sources.map((source) => (
                  <SelectItem key={source} value={source} className="text-[10px] font-bold uppercase tracking-widest">
                    {source === 'all' ? 'All Sources' : source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Geocoding Status Filter - Only for Pending */}
          {mode === 'pending' && (
            <>
              <Separator className="bg-neon-blue/10" />
              <div className="space-y-4">
                <Label className="text-[10px] font-black text-neon-blue uppercase tracking-[0.2em] ml-1">
                  Verification Protocol
                </Label>
                <RadioGroup
                  value={selectedStatus}
                  onValueChange={(value) => setSelectedStatus(value)}
                  className="space-y-2"
                >
                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedStatus === 'all' ? "bg-neon-blue/5 border-neon-blue/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="all" id="all" className="border-neon-blue text-neon-blue" />
                      <Label htmlFor="all" className="text-xs font-black uppercase tracking-widest cursor-pointer">
                        All Signals
                      </Label>
                    </div>
                  </div>

                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedStatus === 'verified' ? "bg-neon-green/5 border-neon-green/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="verified" id="verified" className="border-neon-green text-neon-green" />
                      <Label htmlFor="verified" className="text-xs font-black uppercase tracking-widest cursor-pointer flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4 text-neon-green" />
                        Verified
                      </Label>
                    </div>
                  </div>

                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedStatus === 'ambiguous' ? "bg-warning/5 border-warning/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="ambiguous" id="ambiguous" className="border-warning text-warning" />
                      <Label htmlFor="ambiguous" className="text-xs font-black uppercase tracking-widest cursor-pointer flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-warning" />
                        Ambiguous
                      </Label>
                    </div>
                  </div>

                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedStatus === 'failed' ? "bg-destructive/5 border-destructive/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="failed" id="failed" className="border-destructive text-destructive" />
                      <Label htmlFor="failed" className="text-xs font-black uppercase tracking-widest cursor-pointer flex items-center gap-2">
                        <XCircle className="w-4 h-4 text-destructive" />
                        Failed
                      </Label>
                    </div>
                  </div>
                </RadioGroup>
              </div>
            </>
          )}

          {/* Dedupe Status Filter - Only for Pending */}
          {mode === 'pending' && setSelectedDedupeStatus && dedupeCounts && (
            <>
              <Separator className="bg-neon-blue/10" />
              <div className="space-y-4">
                <Label className="text-[10px] font-black text-neon-blue uppercase tracking-[0.2em] ml-1">
                  Collision Status
                </Label>
                <RadioGroup
                  value={selectedDedupeStatus}
                  onValueChange={(value) => setSelectedDedupeStatus(value)}
                  className="space-y-2"
                >
                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedDedupeStatus === 'all' ? "bg-neon-blue/5 border-neon-blue/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="all" id="dedupe-all" className="border-neon-blue text-neon-blue" />
                      <Label htmlFor="dedupe-all" className="text-xs font-black uppercase tracking-widest cursor-pointer">
                        All Signals
                      </Label>
                    </div>
                  </div>

                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedDedupeStatus === 'not_checked' ? "bg-neon-blue/5 border-neon-blue/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="not_checked" id="dedupe-not-checked" className="border-neon-blue text-neon-blue" />
                      <Label htmlFor="dedupe-not-checked" className="text-xs font-black uppercase tracking-widest cursor-pointer flex items-center gap-2">
                        <ShieldQuestion className="w-4 h-4 text-muted-foreground" />
                        Not Checked
                      </Label>
                    </div>
                  </div>

                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedDedupeStatus === 'possible_match' ? "bg-warning/5 border-warning/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="possible_match" id="dedupe-possible" className="border-warning text-warning" />
                      <Label htmlFor="dedupe-possible" className="text-xs font-black uppercase tracking-widest cursor-pointer flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-warning" />
                        Possible Match
                      </Label>
                    </div>
                  </div>

                  <div className={cn(
                    "flex items-center p-3 rounded-xl border transition-all",
                    selectedDedupeStatus === 'duplicate_confirmed' ? "bg-destructive/5 border-destructive/30" : "bg-transparent border-transparent"
                  )}>
                    <div className="flex items-center space-x-3">
                      <RadioGroupItem value="duplicate_confirmed" id="dedupe-confirmed" className="border-destructive text-destructive" />
                      <Label htmlFor="dedupe-confirmed" className="text-xs font-black uppercase tracking-widest cursor-pointer flex items-center gap-2">
                        <Copy className="w-4 h-4 text-destructive" />
                        Duplicate Confirmed
                      </Label>
                    </div>
                  </div>
                </RadioGroup>
              </div>
            </>
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}

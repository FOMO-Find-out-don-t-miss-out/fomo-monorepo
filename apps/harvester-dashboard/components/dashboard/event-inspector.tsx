'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn, dedupeStatusLabel } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Calendar } from '@/components/ui/calendar'
import type { PendingEvent, GeocodeSuggestion } from '@/types/api'
import { moderationApi } from '@/lib/api'
import {
  ExternalLink,
  Check,
  X,
  RefreshCw,
  Calendar as CalendarIcon,
  MapPin,
  Search,
  ImageOff,
  Flame,
  Plus,
  Code,
  Sparkles,
  Database,
  Copy,
  ShieldQuestion,
  AlertCircle,
  Link2
} from 'lucide-react'
import { format } from 'date-fns'
import { toast } from 'sonner'
import { useMutation, useQueryClient } from '@tanstack/react-query'

interface EventInspectorProps {
  event: PendingEvent | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onApprove: (event: PendingEvent) => void
  onReject: (event: PendingEvent) => void
}

const categories = ['Live Music', 'Theater', 'Art', 'Food & Drink', 'Nightlife', 'Sports', 'Other']

const ingestionConfig: Record<string, { icon: React.ElementType, label: string, color: string }> = {
  json_ld: {
    icon: Code,
    label: 'JSON-LD',
    color: 'text-neon-blue'
  },
  html_fallback: {
    icon: Sparkles,
    label: 'AI Fallback',
    color: 'text-neon-purple'
  },
  registry: {
    icon: Database,
    label: 'Registry',
    color: 'text-neon-yellow'
  },
  manual: {
    icon: Database,
    label: 'Manual',
    color: 'text-muted-foreground'
  }
}

const dedupeIconConfig: Record<string, { icon: React.ElementType, color: string }> = {
  not_checked: { icon: ShieldQuestion, color: 'text-muted-foreground' },
  possible_match: { icon: AlertCircle, color: 'text-warning' },
  duplicate_confirmed: { icon: Copy, color: 'text-destructive' }
}

function DateTimePicker({ 
  value, 
  onChange
}: { 
  value: string | undefined, 
  onChange: (val: string) => void
}) {
  const date = value ? new Date(value) : undefined;
  
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={"outline"}
          className={cn(
            "w-full justify-start text-left font-normal bg-card/40 backdrop-blur-sm input-neon",
            !value && "text-muted-foreground"
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4 text-neon-purple/70" />
          {value ? format(date!, "dd/MM/yyyy HH:mm") : <span>Pick a date</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0 bg-card border-neon-purple/20 shadow-2xl" align="start">
        <Calendar
          mode="single"
          selected={date}
          onSelect={(d) => {
            if (d) {
              const newDate = new Date(value || new Date());
              newDate.setFullYear(d.getFullYear(), d.getMonth(), d.getDate());
              onChange(newDate.toISOString());
            }
          }}
          initialFocus
          className="bg-card"
        />
        <div className="p-3 border-t border-border flex items-center gap-2 bg-muted/20">
          <Input
            type="time"
            value={date ? format(date, "HH:mm") : "00:00"}
            onChange={(e) => {
              const [hours, minutes] = e.target.value.split(":");
              const newDate = new Date(value || new Date());
              newDate.setHours(parseInt(hours), parseInt(minutes));
              onChange(newDate.toISOString());
            }}
            className="w-24 h-8 text-xs bg-card/60 input-neon"
          />
          <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">24h format</span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export function EventInspector({ event, open, onOpenChange, onApprove, onReject }: EventInspectorProps) {
  const queryClient = useQueryClient()
  const [editedEvent, setEditedEvent] = useState<PendingEvent | null>(null)
  const [locationSearch, setLocationSearch] = useState('')
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])
  const [newOccDate, setNewOccDate] = useState<string>('')

  useEffect(() => {
    if (event) {
      setEditedEvent({ ...event })
    }
  }, [event])

  // Fetch suggestions from backend
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

  const syncLocationMutation = useMutation({
    mutationFn: (suggestion: GeocodeSuggestion) => moderationApi.batchUpdateLocation({
      target_name: editedEvent?.location_name || '',
      lat: suggestion.lat,
      lng: suggestion.lng,
      status: suggestion.geocoding_status,
      confidence: suggestion.relevance,
      metadata: suggestion.geocoding_metadata
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success('Location synced for all matching events')
      setSuggestions([])
      setLocationSearch('')
    }
  })

  const addOccurrenceMutation = useMutation({
    mutationFn: (startTime: string) => moderationApi.addOccurrence(editedEvent?.id || '', startTime),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success('Additional date added')
    }
  })

  if (!event || !editedEvent) return null

  // Extract occurrences from metadata
  const occurrences = (editedEvent.event_metadata?.occurrences as Array<{ start_time: string }> | undefined) ?? []

  // Only pk.* tokens are valid for browser/iframe usage; sk.* tokens are server-side only.
  const rawMapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
  const mapboxToken = rawMapboxToken?.startsWith('pk.') ? rawMapboxToken : null

  // Extract coordinates for Mapbox iframe
  let lat = 37.9838, lng = 23.7275 // Default Athens
  
  if (editedEvent.location && typeof editedEvent.location === 'object') {
    const loc = editedEvent.location as { type?: unknown; coordinates?: unknown[] }
    if (loc.type === 'Point' && Array.isArray(loc.coordinates)) {
      lng = loc.coordinates[0] as number
      lat = loc.coordinates[1] as number
    }
  }

  const fullAddress = editedEvent.geocoding_metadata?.full_address || editedEvent.event_metadata?.full_address || null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col bg-card/95 backdrop-blur-xl border-l border-neon-blue/20 shadow-[0_0_50px_rgba(0,0,0,0.5)] h-full">
        <SheetHeader className="sr-only">
          <SheetTitle>Event Details: {event.title}</SheetTitle>
          <SheetDescription>View and edit details for the event {event.title}</SheetDescription>
        </SheetHeader>
        <ScrollArea className="flex-1 min-h-0">
          {/* Image Header */}
          <div className="relative w-full h-56 bg-muted">
            {event.photo_url ? (
              <Image
                src={event.photo_url}
                alt={event.title}
                fill
                className="object-cover transition-transform duration-1000 group-hover:scale-105"
                sizes="(max-width: 640px) 100vw, 576px"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <ImageOff className="w-12 h-12 text-muted-foreground/30" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-card via-card/40 to-transparent" />
            <div className="absolute bottom-6 left-6 right-6">
              <Badge variant="outline" className="badge-neon-purple mb-3 uppercase tracking-widest font-bold">
                {event.category}
              </Badge>
              <h2 className="text-2xl font-black text-foreground text-neon-glow-blue leading-tight tracking-tight uppercase italic">{event.title}</h2>
            </div>
          </div>

          <div className="p-6 space-y-8">
            {/* Basic Info */}
            <div className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="title" className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                  Event Title
                </Label>
                <Input
                  id="title"
                  value={editedEvent.title}
                  onChange={(e) => setEditedEvent({ ...editedEvent, title: e.target.value })}
                  className="bg-card/40 input-neon font-medium"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="venue" className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                  Place Name
                </Label>
                <Input
                  id="venue"
                  value={editedEvent.location_name || ''}
                  onChange={(e) => setEditedEvent({ ...editedEvent, location_name: e.target.value })}
                  className="bg-card/40 input-neon font-medium"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="startTime" className="text-[10px] font-bold text-neon-purple uppercase tracking-[0.2em] ml-1">
                    Start Time
                  </Label>
                  <DateTimePicker
                    value={editedEvent.start_time}
                    onChange={(val) => setEditedEvent({ ...editedEvent, start_time: val })}
                  />                </div>
                <div className="space-y-2">
                  <Label htmlFor="endTime" className="text-[10px] font-bold text-neon-purple uppercase tracking-[0.2em] ml-1">
                    End Time
                  </Label>
                  <DateTimePicker
                    value={editedEvent.end_time || undefined}
                    onChange={(val) => setEditedEvent({ ...editedEvent, end_time: val })}
                  />                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                    Category
                  </Label>
                  <Select
                    value={editedEvent.category}
                    onValueChange={(value) => setEditedEvent({ ...editedEvent, category: value })}
                  >
                    <SelectTrigger className="bg-card/40 input-neon font-medium">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-card border-neon-blue/20">
                      {categories.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="hypeScore" className="text-[10px] font-bold text-neon-pink uppercase tracking-[0.2em] ml-1 flex items-center gap-1">
                    <Flame className="w-3 h-3 text-neon-pink animate-pulse" />
                    Hype Score
                  </Label>
                  <Input
                    id="hypeScore"
                    type="number"
                    min="0"
                    max="100"
                    value={editedEvent.hype_score}
                    onChange={(e) => setEditedEvent({ ...editedEvent, hype_score: parseInt(e.target.value) || 0 })}
                    className="bg-card/40 input-neon font-bold text-neon-pink"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="ticketUrl" className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                  Ticket URL
                </Label>
                <div className="relative group">
                  <Input
                    id="ticketUrl"
                    value={editedEvent.ticket_url || ''}
                    onChange={(e) => setEditedEvent({ ...editedEvent, ticket_url: e.target.value })}
                    placeholder="https://"
                    className="bg-card/40 input-neon pr-10"
                  />
                  {editedEvent.ticket_url && (
                    <a 
                      href={editedEvent.ticket_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-neon-blue transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Additional Dates */}
            <div className="space-y-4 pt-4 border-t border-neon-purple/10">
              <Label className="text-[10px] font-bold text-neon-purple uppercase tracking-[0.2em] ml-1 flex items-center gap-2">
                <CalendarIcon className="w-4 h-4" />
                Additional Dates (Recurring)
              </Label>
              
              {occurrences.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {occurrences.map((occ: { start_time: string }, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-card/40 border border-neon-purple/20 group hover:border-neon-purple/50 transition-colors">
                      <span className="text-xs font-medium">
                        {format(new Date(occ.start_time), 'dd MMM, HH:mm')}
                      </span>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-6 w-6 p-0 text-muted-foreground hover:text-neon-red hover:bg-neon-red/10"
                        onClick={() => {
                            const newOcc = [...occurrences];
                            newOcc.splice(idx, 1);
                            setEditedEvent({
                                ...editedEvent,
                                event_metadata: { ...editedEvent.event_metadata, occurrences: newOcc }
                            });
                        }}
                      >
                        <X className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <div className="flex-1">
                  <DateTimePicker
                    value={newOccDate}
                    onChange={setNewOccDate}
                  />                </div>
                <Button 
                  size="sm" 
                  variant="neon-purple"
                  className="h-9 px-4 font-bold"
                  onClick={() => {
                    if (newOccDate) {
                      addOccurrenceMutation.mutate(new Date(newOccDate).toISOString());
                      setNewOccDate('');
                    }
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add
                </Button>
              </div>
            </div>

            {/* Source Info */}
            <div className="p-4 rounded-xl bg-muted/20 border border-border/50 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-neon-blue/60" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">
                    Source: {event.source_provider || 'unknown'}
                  </span>
                </div>
                <Badge variant="outline" className="badge-neon h-5 px-2 gap-2 font-bold uppercase tracking-tighter">
                  {(() => {
                    const Ingestion = ingestionConfig[event.ingestion_method] || ingestionConfig.manual
                    const Icon = Ingestion.icon
                    return (
                      <>
                        <Icon className={cn("w-3 h-3", Ingestion.color)} />
                        {Ingestion.label}
                      </>
                    )
                  })()}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {(() => {
                    const Dedupe = dedupeIconConfig[event.dedupe_status] || dedupeIconConfig.not_checked
                    const Icon = Dedupe.icon
                    return <Icon className={cn("w-4 h-4", Dedupe.color)} />
                  })()}
                  <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">
                    Dedupe: {dedupeStatusLabel(event.dedupe_status)}
                  </span>
                </div>
                {event.candidate_event_id && (
                  <Badge variant="outline" className="h-5 px-2 gap-2 font-bold uppercase tracking-tighter border-neon-blue/30 text-neon-blue bg-neon-blue/5">
                    <Link2 className="w-3 h-3" />
                    Candidate linked
                  </Badge>
                )}
              </div>
              <Button variant="neon" size="sm" className="w-full font-bold uppercase tracking-widest text-[10px]" asChild>
                <a href={event.source_url || '#'} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-3.5 h-3.5 mr-2" />
                  Inspect Original Source
                </a>
              </Button>
            </div>

            {/* Map Section */}
            <div className="space-y-3 pt-4 border-t border-neon-blue/10">
              <div className="flex items-center justify-between">
                <Label className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1 flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  Geocoding: {editedEvent.geocoding_status}
                </Label>
                <div className="text-[10px] font-mono text-muted-foreground bg-card/60 px-2 py-0.5 rounded border border-border/50">
                  {lat.toFixed(6)}, {lng.toFixed(6)}
                </div>
              </div>
              
              <div className="rounded-xl overflow-hidden border border-neon-blue/30 shadow-[0_0_15px_rgba(37,99,235,0.1)] group">
                <div className="h-48 bg-muted relative">
                  {mapboxToken ? (
                    <>
                      <iframe
                        src={`https://api.mapbox.com/styles/v1/mapbox/dark-v11.html?title=false&access_token=${mapboxToken}&zoomwheel=false#15/${lat}/${lng}`}
                        className="w-full h-full border-0 grayscale-[0.5] contrast-[1.2] brightness-[0.8] group-hover:grayscale-0 group-hover:brightness-100 transition-all duration-500"
                        title="Event Location"
                      />
                      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
                        <div className="w-5 h-5 bg-neon-blue rounded-full border-2 border-white neon-glow-blue animate-neon-pulse" />
                      </div>
                    </>
                  ) : (
                    <div className="w-full h-full flex flex-col items-center justify-center gap-2 text-muted-foreground/60">
                      <MapPin className="w-7 h-7 opacity-30" />
                      <p className="text-[11px] font-medium text-center px-4">
                        Map is unavailable because the Mapbox public token is not configured correctly.
                      </p>
                    </div>
                  )}
                </div>
              </div>
              
              {fullAddress && (
                <div className="p-3 rounded-lg bg-card/60 border border-border/50 text-[11px] font-medium leading-relaxed italic text-muted-foreground/90">
                  {fullAddress as string}
                </div>
              )}
            </div>

            {/* Location Search */}
            <div className="space-y-3 pb-8">
              <Label className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                Refine Geolocation
              </Label>
              <div className="relative">
                <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-neon-blue transition-colors" />
                <Input
                  placeholder="Type to search Mapbox Registry..."
                  value={locationSearch}
                  onChange={(e) => setLocationSearch(e.target.value)}
                  className="pl-10 bg-card/40 input-neon h-10"
                />
              </div>
              {suggestions.length > 0 && (
                <div className="border border-neon-blue/20 rounded-xl overflow-hidden bg-card/80 backdrop-blur-md shadow-2xl animate-in fade-in slide-in-from-top-2 duration-300">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      className="w-full p-4 text-left hover:bg-neon-blue/10 transition-all border-b border-neon-blue/10 last:border-b-0 group"
                      onClick={() => syncLocationMutation.mutate(suggestion)}
                      disabled={syncLocationMutation.isPending}
                    >
                      <div className="font-bold text-sm text-foreground group-hover:text-neon-blue transition-colors">{suggestion.full_address}</div>
                      <div className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mt-1">{suggestion.city}, {suggestion.country_code}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </ScrollArea>

        {/* Action Buttons */}
        <div className="p-6 border-t border-neon-blue/20 bg-card/90 backdrop-blur-xl sticky bottom-0 z-30 space-y-3 shadow-[0_-10px_30px_rgba(0,0,0,0.3)]">
          <div className="grid grid-cols-2 gap-3">
            {event.status === 'published' ? (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="neon-red"
                    className="col-span-2 h-11 font-black uppercase tracking-[0.2em]"
                  >
                    <X className="w-5 h-5 mr-3" />
                    Unpublish Event
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent className="bg-card border-neon-red/40">
                  <AlertDialogHeader>
                    <AlertDialogTitle className="text-neon-red uppercase font-black tracking-tighter">Unpublish this event?</AlertDialogTitle>
                    <AlertDialogDescription className="text-muted-foreground font-medium">
                      &quot;{event.title}&quot; will be removed from the live feed immediately. If a
                      matching pending signal still exists it will return to Pending Signals for
                      re-review; otherwise this record is gone for good.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel className="bg-card border-border uppercase font-bold tracking-widest text-[10px]">Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      className="bg-neon-red hover:bg-neon-red/80 text-white font-black uppercase tracking-[0.2em] text-[10px]"
                      onClick={() => onReject(editedEvent)}
                    >
                      Confirm Unpublish
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            ) : (
              <>
                <Button
                  variant="neon-green"
                  className="h-11 font-black uppercase tracking-[0.2em]"
                  onClick={() => onApprove(editedEvent)}
                >
                  <Check className="w-5 h-5 mr-2" />
                  Approve
                </Button>
                <Button
                  variant="neon-red"
                  className="h-11 font-black uppercase tracking-[0.2em]"
                  onClick={() => onReject(editedEvent)}
                >
                  <X className="w-5 h-5 mr-2" />
                  Reject
                </Button>
              </>
            )}
          </div>
          <div className="grid grid-cols-1 gap-3">
            <Button
                variant="neon-purple"
                size="sm"
                className="h-9 font-bold uppercase tracking-widest text-[10px]"
                onClick={() => {
                  const updateFn = event.status === 'published' 
                    ? moderationApi.updatePublishedEvent 
                    : moderationApi.updateEvent;
                  
                  updateFn(editedEvent.id, {
                    title: editedEvent.title,
                    location_name: editedEvent.location_name,
                    category: editedEvent.category,
                    hype_score: editedEvent.hype_score,
                    ticket_url: editedEvent.ticket_url,
                    event_metadata: editedEvent.event_metadata,
                    start_time: editedEvent.start_time,
                    end_time: editedEvent.end_time
                  }).then(() => {
                    queryClient.invalidateQueries({ queryKey: ['pending-events'] });
                    queryClient.invalidateQueries({ queryKey: ['published-events'] });
                    toast.success('Event updated');
                  })
                }}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Save Changes
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

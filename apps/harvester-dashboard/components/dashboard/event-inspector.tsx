'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
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
import { Calendar } from '@/components/ui/calendar'
import type { PendingEvent, GeocodeSuggestion } from '@/types/moderation'
import { moderationApi } from '@/lib/api'
import {
  ExternalLink,
  Check,
  X,
  GitMerge,
  RefreshCw,
  Calendar as CalendarIcon,
  MapPin,
  Search,
  ImageOff,
  Flame,
  Plus,
  Code,
  Sparkles,
  Database
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
    color: 'text-blue-500'
  },
  html_fallback: {
    icon: Sparkles,
    label: 'AI Fallback',
    color: 'text-purple-500'
  },
  registry: {
    icon: Database,
    label: 'Registry',
    color: 'text-amber-500'
  },
  manual: {
    icon: Database,
    label: 'Manual',
    color: 'text-gray-500'
  }
}

function DateTimePicker({ 
  value, 
  onChange, 
  label 
}: { 
  value: string | undefined, 
  onChange: (val: string) => void,
  label: string
}) {
  const date = value ? new Date(value) : undefined;
  
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={"outline"}
          className={cn(
            "w-full justify-start text-left font-normal bg-input/50",
            !value && "text-muted-foreground"
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {value ? format(date!, "dd/MM/yyyy HH:mm") : <span>Pick a date</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
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
        />
        <div className="p-3 border-t border-border flex items-center gap-2">
          <Input
            type="time"
            value={date ? format(date, "HH:mm") : "00:00"}
            onChange={(e) => {
              const [hours, minutes] = e.target.value.split(":");
              const newDate = new Date(value || new Date());
              newDate.setHours(parseInt(hours), parseInt(minutes));
              onChange(newDate.toISOString());
            }}
            className="w-24 h-8 text-xs"
          />
          <span className="text-xs text-muted-foreground">24h format</span>
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
  const occurrences = editedEvent.event_metadata?.occurrences || []

  // Extract coordinates for Mapbox iframe
  // location might be a WKT string like "POINT(lng lat)" OR a GeoJSON object {"type": "Point", "coordinates": [lng, lat]}
  let lat = 37.9838, lng = 23.7275 // Default Athens
  
  if (editedEvent.location) {
    if (typeof editedEvent.location === 'string' && editedEvent.location.startsWith('POINT')) {
      const coords = editedEvent.location.match(/POINT\((.+) (.+)\)/)
      if (coords) {
        lng = parseFloat(coords[1])
        lat = parseFloat(coords[2])
      }
    } else if (typeof editedEvent.location === 'object' && editedEvent.location.type === 'Point' && Array.isArray(editedEvent.location.coordinates)) {
      lng = editedEvent.location.coordinates[0]
      lat = editedEvent.location.coordinates[1]
    }
  }

  const fullAddress = editedEvent.geocoding_metadata?.full_address || editedEvent.event_metadata?.full_address || null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col bg-card border-l border-border h-full">
        <SheetHeader className="sr-only">
          <SheetTitle>Event Details: {event.title}</SheetTitle>
          <SheetDescription>View and edit details for the event {event.title}</SheetDescription>
        </SheetHeader>
        <ScrollArea className="flex-1 min-h-0">
          {/* Image Header */}
          <div className="relative w-full h-48 bg-muted">
            {event.photo_url ? (
              <Image
                src={event.photo_url}
                alt={event.title}
                fill
                className="object-cover"
                sizes="(max-width: 640px) 100vw, 576px"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <ImageOff className="w-12 h-12 text-muted-foreground" />
              </div>
            )}
            <div className="absolute inset-0 bg-gradient-to-t from-background/90 to-transparent" />
            <div className="absolute bottom-4 left-4 right-4">
              <Badge variant="secondary" className="mb-2">
                {event.category}
              </Badge>
              <h2 className="text-lg font-semibold text-foreground">{event.title}</h2>
            </div>
          </div>

          <div className="p-4 space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title" className="text-xs text-muted-foreground uppercase tracking-wider">
                  Title
                </Label>
                <Input
                  id="title"
                  value={editedEvent.title}
                  onChange={(e) => setEditedEvent({ ...editedEvent, title: e.target.value })}
                  className="bg-input/50"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="venue" className="text-xs text-muted-foreground uppercase tracking-wider">
                  Venue Name
                </Label>
                <Input
                  id="venue"
                  value={editedEvent.location_name || ''}
                  onChange={(e) => setEditedEvent({ ...editedEvent, location_name: e.target.value })}
                  className="bg-input/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="startTime" className="text-xs text-muted-foreground uppercase tracking-wider">
                    Start Time
                  </Label>
                  <DateTimePicker 
                    label="Start Time"
                    value={editedEvent.start_time} 
                    onChange={(val) => setEditedEvent({ ...editedEvent, start_time: val })} 
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="endTime" className="text-xs text-muted-foreground uppercase tracking-wider">
                    End Time
                  </Label>
                  <DateTimePicker 
                    label="End Time"
                    value={editedEvent.end_time || undefined} 
                    onChange={(val) => setEditedEvent({ ...editedEvent, end_time: val })} 
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                    Category
                  </Label>
                  <Select
                    value={editedEvent.category}
                    onValueChange={(value) => setEditedEvent({ ...editedEvent, category: value })}
                  >
                    <SelectTrigger className="bg-input/50">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="hypeScore" className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                    <Flame className="w-3 h-3" />
                    Hype Score
                  </Label>
                  <Input
                    id="hypeScore"
                    type="number"
                    min="0"
                    max="100"
                    value={editedEvent.hype_score}
                    onChange={(e) => setEditedEvent({ ...editedEvent, hype_score: parseInt(e.target.value) || 0 })}
                    className="bg-input/50"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="ticketUrl" className="text-xs text-muted-foreground uppercase tracking-wider">
                  Ticket URL
                </Label>
                <Input
                  id="ticketUrl"
                  value={editedEvent.ticket_url || ''}
                  onChange={(e) => setEditedEvent({ ...editedEvent, ticket_url: e.target.value })}
                  placeholder="https://"
                  className="bg-input/50"
                />
              </div>
            </div>

            {/* Additional Dates */}
            <Separator className="bg-border" />
            <div className="space-y-4">
              <Label className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                <CalendarIcon className="w-3 h-3" />
                Additional Dates (Recurring)
              </Label>
              
              {occurrences.length > 0 && (
                <div className="space-y-2">
                  {occurrences.map((occ: { start_time: string }, idx: number) => (
                    <div key={idx} className="flex items-center justify-between p-2 rounded-md bg-muted/50 border border-border">
                      <span className="text-sm">
                        {format(new Date(occ.start_time), 'dd/MM/yyyy HH:mm')}
                      </span>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-7 w-7 p-0 text-destructive"
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
                    label="New Date"
                    value={newOccDate} 
                    onChange={setNewOccDate} 
                  />
                </div>
                <Button 
                  size="sm" 
                  variant="outline"
                  className="h-9"
                  onClick={() => {
                    if (newOccDate) {
                      addOccurrenceMutation.mutate(new Date(newOccDate).toISOString());
                      setNewOccDate('');
                    }
                  }}
                >
                  <Plus className="w-4 h-4 mr-1" />
                  Add
                </Button>
              </div>
            </div>

            {/* Source */}
            <Separator className="bg-border" />
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Database className="w-3 h-3" />
                  Source: {event.source_provider || 'unknown'}
                </Label>
                <Badge variant="outline" className="text-[10px] h-5 px-1.5 gap-1.5 font-normal">
                  {(() => {
                    const Ingestion = ingestionConfig[event.ingestion_method] || ingestionConfig.manual
                    const Icon = Ingestion.icon
                    return (
                      <>
                        <Icon className={cn("w-2.5 h-2.5", Ingestion.color)} />
                        {Ingestion.label}
                      </>
                    )
                  })()}
                </Badge>
              </div>
              <Button variant="outline" size="sm" className="w-full justify-start" asChild>
                <a href={event.source_url || '#'} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  View Original Page
                </a>
              </Button>
            </div>

            {/* Map */}
            <Separator className="bg-border" />
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                Location ({editedEvent.geocoding_status})
              </Label>
              <div className="rounded-lg overflow-hidden border border-border">
                <div className="h-40 bg-muted relative">
                  <iframe
                    src={`https://api.mapbox.com/styles/v1/mapbox/dark-v11.html?title=false&access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw&zoomwheel=false#15/${lat}/${lng}`}
                    className="w-full h-full border-0"
                    title="Event Location"
                  />
                  <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
                    <div className="w-4 h-4 bg-primary rounded-full border-2 border-primary-foreground shadow-lg" />
                  </div>
                </div>
              </div>
              <div className="text-xs text-muted-foreground">
                {lat.toFixed(4)}, {lng.toFixed(4)}
              </div>
              {fullAddress && (
                <div className="text-[10px] text-muted-foreground/80 italic mt-1">
                  {fullAddress as string}
                </div>
              )}
            </div>

            {/* Location Search */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                Find & Sync Location
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search for a location..."
                  value={locationSearch}
                  onChange={(e) => setLocationSearch(e.target.value)}
                  className="pl-9 bg-input/50"
                />
              </div>
              {suggestions.length > 0 && (
                <div className="border border-border rounded-lg overflow-hidden">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      className="w-full p-3 text-left hover:bg-accent transition-colors border-b border-border last:border-b-0"
                      onClick={() => syncLocationMutation.mutate(suggestion)}
                      disabled={syncLocationMutation.isPending}
                    >
                      <div className="font-medium text-sm text-foreground">{suggestion.full_address}</div>
                      <div className="text-xs text-muted-foreground">{suggestion.city}, {suggestion.country_code}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </ScrollArea>

        {/* Action Buttons */}
        <div className="p-4 border-t border-border bg-card/80 backdrop-blur-sm sticky bottom-0">
          <div className="grid grid-cols-2 gap-2 mb-2">
            {event.status === 'published' ? (
              <Button
                variant="destructive"
                className="col-span-2"
                onClick={() => onReject(editedEvent)}
              >
                <X className="w-4 h-4 mr-2" />
                Unpublish Event
              </Button>
            ) : (
              <>
                <Button
                  variant="default"
                  className="bg-green-600 hover:bg-green-700 text-white"
                  onClick={() => onApprove(editedEvent)}
                >
                  <Check className="w-4 h-4 mr-2" />
                  Approve
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => onReject(editedEvent)}
                >
                  <X className="w-4 h-4 mr-2" />
                  Reject
                </Button>
              </>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline" size="sm" onClick={() => toast.info('Merge feature coming soon')}>
              <GitMerge className="w-4 h-4 mr-2" />
              Merge Venue
            </Button>
            <Button 
                variant="outline" 
                size="sm" 
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

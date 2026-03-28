'use client'

import { useState, useEffect } from 'react'
import { Sheet, SheetContent } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
import type { Venue, GeocodeSuggestion } from '@/types/moderation'
import { moderationApi } from '@/lib/api'
import {
  GitMerge,
  Trash2,
  Save,
  CheckCircle2,
  Calendar,
  ChevronRight, MapPin, Search
} from 'lucide-react'
import { format } from 'date-fns'
import { toast } from 'sonner'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

interface VenueInspectorProps {
  venue: Venue | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function VenueInspector({ venue, open, onOpenChange }: VenueInspectorProps) {
  const queryClient = useQueryClient()
  const [editedVenue, setEditedVenue] = useState<Venue | null>(null)
  const [locationSearch, setLocationSearch] = useState('')
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([])
  const [applyToAll, setApplyToAll] = useState(false)
  const [targetVenueId, setTargetVenueId] = useState<string | null>(null)

  // Fetch linked events
  const { data: linkedEvents = [] } = useQuery({
    queryKey: ['venue-linked-events', venue?.name],
    queryFn: () => moderationApi.getPendingEvents(venue?.name || undefined),
    enabled: !!venue?.name
  })

  // Fetch all venues for merge selection
  const { data: allVenues = [] } = useQuery({
    queryKey: ['all-venues-for-merge'],
    queryFn: () => moderationApi.getVenues(),
    enabled: open
  })

  useEffect(() => {
    if (venue) {
      setEditedVenue({ ...venue })
    }
  }, [venue])

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

  const saveMutation = useMutation({
    mutationFn: async (v: Venue) => {
      const updated = await moderationApi.updateVenue(v.id, {
        name: v.name,
        city: v.city,
        full_address: v.full_address,
        lat: v.lat,
        lng: v.lng,
        is_manually_verified: v.is_manually_verified
      })
      
      if (applyToAll) {
        await moderationApi.batchUpdateLocation({
          target_name: v.name,
          lat: v.lat,
          lng: v.lng,
          status: v.is_manually_verified ? 'verified' : 'ambiguous',
          confidence: 1.0,
          metadata: { source: 'manual_venue_update', full_address: v.full_address, city: v.city }
        })
      }
      return updated
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['venues'] })
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success('Venue saved successfully')
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => moderationApi.deleteVenue(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['venues'] })
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success('Venue deleted')
      onOpenChange(false)
    }
  })

  const mergeMutation = useMutation({
    mutationFn: (targetId: string) => moderationApi.mergeVenues(venue?.id || '', targetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['venues'] })
      queryClient.invalidateQueries({ queryKey: ['pending-events'] })
      toast.success('Venues merged successfully')
      onOpenChange(false)
    }
  })

  const handleLocationSelect = (suggestion: GeocodeSuggestion) => {
    if (editedVenue) {
      setEditedVenue({
        ...editedVenue,
        lat: suggestion.lat,
        lng: suggestion.lng,
        full_address: suggestion.full_address,
        city: suggestion.city || editedVenue.city
      })
      setLocationSearch('')
      setSuggestions([])
      toast.success('Coordinates updated from suggestion')
    }
  }

  if (!venue || !editedVenue) return null

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col bg-card border-l border-border h-full">
        <ScrollArea className="flex-1 min-h-0">
          {/* Map Header */}
          <div className="relative w-full h-48 bg-muted">
            <iframe
              src={`https://api.mapbox.com/styles/v1/mapbox/dark-v11.html?title=false&access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw&zoomwheel=false#14/${editedVenue.lat}/${editedVenue.lng}`}
              className="w-full h-full border-0"
              title="Venue Location"
            />
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
              <div className="w-5 h-5 bg-primary rounded-full border-2 border-primary-foreground shadow-lg" />
            </div>
            <div className="absolute top-4 right-12">
              <Badge
                variant={editedVenue.is_manually_verified ? 'default' : 'secondary'}
                className={editedVenue.is_manually_verified ? 'bg-green-600 text-white' : ''}
              >
                {editedVenue.is_manually_verified ? 'Verified' : 'Unverified'}
              </Badge>
            </div>
          </div>

          <div className="p-4 space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="venueTitle" className="text-xs text-muted-foreground uppercase tracking-wider">
                  Venue Name
                </Label>
                <Input
                  id="venueTitle"
                  value={editedVenue.name}
                  onChange={(e) => setEditedVenue({ ...editedVenue, name: e.target.value })}
                  className="bg-input/50"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="city" className="text-xs text-muted-foreground uppercase tracking-wider">
                  City
                </Label>
                <Input
                  id="city"
                  value={editedVenue.city || ''}
                  onChange={(e) => setEditedVenue({ ...editedVenue, city: e.target.value })}
                  className="bg-input/50"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="address" className="text-xs text-muted-foreground uppercase tracking-wider">
                  Full Address
                </Label>
                <Input
                  id="address"
                  value={editedVenue.full_address}
                  onChange={(e) => setEditedVenue({ ...editedVenue, full_address: e.target.value })}
                  className="bg-input/50"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="latitude" className="text-xs text-muted-foreground uppercase tracking-wider">
                    Latitude
                  </Label>
                  <Input
                    id="latitude"
                    type="number"
                    step="0.0001"
                    value={editedVenue.lat}
                    onChange={(e) => setEditedVenue({ ...editedVenue, lat: parseFloat(e.target.value) || 0 })}
                    className="bg-input/50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="longitude" className="text-xs text-muted-foreground uppercase tracking-wider">
                    Longitude
                  </Label>
                  <Input
                    id="longitude"
                    type="number"
                    step="0.0001"
                    value={editedVenue.lng}
                    onChange={(e) => setEditedVenue({ ...editedVenue, lng: parseFloat(e.target.value) || 0 })}
                    className="bg-input/50"
                  />
                </div>
              </div>

              {/* Manual Verified Toggle */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50 border border-border">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                  <div>
                    <Label htmlFor="verified" className="text-sm font-medium cursor-pointer">
                      Manual Verified
                    </Label>
                    <p className="text-xs text-muted-foreground">Mark this venue as manually verified</p>
                  </div>
                </div>
                <Switch
                  id="verified"
                  checked={editedVenue.is_manually_verified}
                  onCheckedChange={(checked) => setEditedVenue({ ...editedVenue, is_manually_verified: checked })}
                />
              </div>

              {/* Sync Flag */}
              <div className="flex items-center space-x-2 p-3 rounded-lg border border-dashed border-primary/30 bg-primary/5">
                <Checkbox 
                    id="syncAll" 
                    checked={applyToAll} 
                    onCheckedChange={(checked) => setApplyToAll(checked === true)} 
                />
                <div className="grid gap-1.5 leading-none">
                  <label
                    htmlFor="syncAll"
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                  >
                    Apply to all events at this venue
                  </label>
                  <p className="text-xs text-muted-foreground">
                    This will update the location and status for all published and pending events.
                  </p>
                </div>
              </div>

              {/* Linked Events */}
              <div className="space-y-3">
                <Label className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  Linked Pending Events ({linkedEvents.length})
                </Label>
                {linkedEvents.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
                    {linkedEvents.map((ev) => (
                      <div key={ev.id} className="flex items-center justify-between p-2 rounded-md bg-muted/30 border border-border group hover:bg-muted/50 transition-colors">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium truncate">{ev.title}</p>
                          <p className="text-[10px] text-muted-foreground">
                            {format(new Date(ev.start_time), 'MMM d, yyyy')}
                          </p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground italic">No pending events linked to this venue name.</p>
                )}
              </div>
            </div>

            {/* Location Search */}
            <Separator className="bg-border" />
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                Live Mapbox Suggestions
              </Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search for an address..."
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
                      onClick={() => handleLocationSelect(suggestion)}
                    >
                      <div className="font-medium text-sm text-foreground">{suggestion.full_address}</div>
                      <div className="text-xs text-muted-foreground">{suggestion.city}, {suggestion.country_code}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Merge Venue */}
            <Separator className="bg-border" />
            <div className="space-y-4">
              <div className="flex items-center gap-1.5">
                <GitMerge className="w-4 h-4 text-primary" />
                <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                  Merge INTO another venue
                </Label>
              </div>
              <p className="text-xs text-muted-foreground">
                This will move all events from &quot;{venue.name}&quot; to the selected venue and delete this record.
              </p>
              
              <div className="space-y-3">
                <Select value={targetVenueId || ''} onValueChange={setTargetVenueId}>
                    <SelectTrigger className="bg-input/50">
                        <SelectValue placeholder="Select target venue..." />
                    </SelectTrigger>
                    <SelectContent>
                        {allVenues
                          .filter(v => v.id !== venue.id)
                          .map(v => (
                            <SelectItem key={v.id} value={v.id}>
                                {v.name} ({v.city || 'Unknown City'})
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <AlertDialog>
                    <AlertDialogTrigger asChild>
                        <Button 
                            variant="outline" 
                            className="w-full border-primary/30 hover:bg-primary/10 text-primary"
                            disabled={!targetVenueId || mergeMutation.isPending}
                        >
                            <GitMerge className="w-4 h-4 mr-2" />
                            {mergeMutation.isPending ? 'Merging...' : 'Merge Venues'}
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Confirm Merge</AlertDialogTitle>
                            <AlertDialogDescription>
                                This action is irreversible. All events linked to &quot;{venue.name}&quot; will be updated to point to the new venue, and &quot;{venue.name}&quot; will be deleted.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction
                                onClick={() => targetVenueId && mergeMutation.mutate(targetVenueId)}
                            >
                                Confirm Merge
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          </div>
        </ScrollArea>

        {/* Action Buttons */}
        <div className="p-4 border-t border-border bg-card/80 backdrop-blur-sm sticky bottom-0 space-y-2">
          <Button
            className="w-full"
            onClick={() => saveMutation.mutate(editedVenue)}
            disabled={saveMutation.isPending}
          >
            <Save className="w-4 h-4 mr-2" />
            {saveMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" className="w-full">
                <Trash2 className="w-4 h-4 mr-2" />
                Delete Venue
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete Venue</AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to delete &quot;{venue.name}&quot;? This will unlink it from all events.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive text-white hover:bg-destructive/90"
                  onClick={() => deleteMutation.mutate(venue.id)}
                >
                  Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </SheetContent>
    </Sheet>
  )
}

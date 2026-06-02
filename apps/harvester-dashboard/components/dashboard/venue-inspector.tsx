'use client'

import { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
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
import type { Venue, GeocodeSuggestion } from '@/types/api'
import { moderationApi } from '@/lib/api'
import {
  GitMerge,
  Trash2,
  Save,
  CheckCircle2,
  Calendar,
  ChevronRight, Search, ExternalLink, Building2
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

  // Fetch linked pending events
  const { data: linkedPending = [] } = useQuery({
    queryKey: ['venue-linked-pending', venue?.name],
    queryFn: () => moderationApi.getPendingEvents(venue?.name || undefined),
    enabled: !!venue?.name
  })

  // Fetch linked published events
  const { data: linkedPublished = [] } = useQuery({
    queryKey: ['venue-linked-published', venue?.name],
    queryFn: () => moderationApi.getPublishedEvents(venue?.name || undefined),
    enabled: !!venue?.name
  })

  const allLinkedEvents = useMemo(() => [
    ...linkedPublished.map(e => ({ ...e, isPublished: true })),
    ...linkedPending.map(e => ({ ...e, isPublished: false }))
  ], [linkedPublished, linkedPending])

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
      <SheetContent className="w-full sm:max-w-xl p-0 flex flex-col bg-card/95 backdrop-blur-xl border-l border-neon-blue/20 shadow-[0_0_50px_rgba(0,0,0,0.5)] h-full">
        <SheetHeader className="sr-only">
          <SheetTitle>Venue Details: {venue.name}</SheetTitle>
          <SheetDescription>View and edit details for venue {venue.name}</SheetDescription>
        </SheetHeader>
        <ScrollArea className="flex-1 min-h-0 scrollbar-neon">
          {/* Map Header */}
          <div className="relative w-full h-56 bg-muted">
            <iframe
              src={`https://api.mapbox.com/styles/v1/mapbox/dark-v11.html?title=false&access_token=${process.env.NEXT_PUBLIC_MAPBOX_TOKEN ?? ''}&zoomwheel=false#14/${editedVenue.lat}/${editedVenue.lng}`}
              className="w-full h-full border-0 grayscale-[0.5] contrast-[1.2] brightness-[0.8]"
              title="Venue Location"
            />
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 pointer-events-none">
              <div className="w-6 h-6 bg-neon-blue rounded-full border-2 border-white neon-glow-blue animate-neon-pulse" />
            </div>
            
            <div className="absolute inset-0 bg-gradient-to-t from-card via-card/20 to-transparent pointer-events-none" />
            
            <div className="absolute bottom-6 left-6 right-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-neon-blue/20 backdrop-blur-md border border-neon-blue/30 flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-neon-blue" />
                </div>
                <Badge
                    variant="outline"
                    className={cn(
                        "uppercase tracking-widest font-black h-5 px-2",
                        editedVenue.is_manually_verified ? 'badge-neon-green' : 'badge-neon-purple opacity-70'
                    )}
                >
                    {editedVenue.is_manually_verified ? 'Verified Node' : 'Unverified Node'}
                </Badge>
              </div>
              <h2 className="text-2xl font-black text-foreground text-neon-glow-blue leading-tight tracking-tight uppercase italic truncate">
                {venue.name}
              </h2>
            </div>
          </div>

          <div className="p-6 space-y-8">
            {/* Basic Info */}
            <div className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="venueTitle" className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                  Registry Name
                </Label>
                <Input
                  id="venueTitle"
                  value={editedVenue.name}
                  onChange={(e) => setEditedVenue({ ...editedVenue, name: e.target.value })}
                  className="bg-card/40 input-neon font-bold"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city" className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                    City Node
                  </Label>
                  <Input
                    id="city"
                    value={editedVenue.city || ''}
                    onChange={(e) => setEditedVenue({ ...editedVenue, city: e.target.value })}
                    className="bg-card/40 input-neon font-medium"
                  />
                </div>
                <div className="space-y-2">
                    <Label className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                        Country
                    </Label>
                    <div className="h-10 px-3 flex items-center rounded-md bg-card/20 border border-border/50 text-sm font-bold text-muted-foreground uppercase tracking-widest">
                        {venue.country_code || 'GR'}
                    </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="address" className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1">
                  Physical Protocol (Address)
                </Label>
                <Input
                  id="address"
                  value={editedVenue.full_address}
                  onChange={(e) => setEditedVenue({ ...editedVenue, full_address: e.target.value })}
                  className="bg-card/40 input-neon font-medium"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="latitude" className="text-[10px] font-bold text-neon-purple uppercase tracking-[0.2em] ml-1">
                    Latitude
                  </Label>
                  <Input
                    id="latitude"
                    type="number"
                    step="0.0001"
                    value={editedVenue.lat}
                    onChange={(e) => setEditedVenue({ ...editedVenue, lat: parseFloat(e.target.value) || 0 })}
                    className="bg-card/40 input-neon font-mono text-xs"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="longitude" className="text-[10px] font-bold text-neon-purple uppercase tracking-[0.2em] ml-1">
                    Longitude
                  </Label>
                  <Input
                    id="longitude"
                    type="number"
                    step="0.0001"
                    value={editedVenue.lng}
                    onChange={(e) => setEditedVenue({ ...editedVenue, lng: parseFloat(e.target.value) || 0 })}
                    className="bg-card/40 input-neon font-mono text-xs"
                  />
                </div>
              </div>

              {/* Manual Verified Toggle */}
              <div className={cn(
                  "flex items-center justify-between p-4 rounded-xl transition-all duration-300 border",
                  editedVenue.is_manually_verified 
                    ? "bg-neon-green/5 border-neon-green/20 neon-glow-sm-green" 
                    : "bg-muted/10 border-border/50"
              )}>
                <div className="flex items-center gap-3">
                  <CheckCircle2 className={cn(
                      "w-5 h-5 transition-colors",
                      editedVenue.is_manually_verified ? "text-neon-green text-neon-glow-green" : "text-muted-foreground"
                  )} />
                  <div>
                    <Label htmlFor="verified" className="text-xs font-black uppercase tracking-widest cursor-pointer">
                      Manual Verification
                    </Label>
                    <p className="text-[10px] text-muted-foreground uppercase font-bold tracking-tight opacity-70">Elevate node to trusted status</p>
                  </div>
                </div>
                <Switch
                  id="verified"
                  checked={editedVenue.is_manually_verified}
                  onCheckedChange={(checked) => setEditedVenue({ ...editedVenue, is_manually_verified: checked })}
                  className="data-[state=checked]:bg-neon-green"
                />
              </div>

              {/* Sync Flag */}
              <div className="flex items-center space-x-3 p-4 rounded-xl border border-dashed border-neon-blue/30 bg-neon-blue/5">
                <Checkbox 
                    id="syncAll" 
                    checked={applyToAll} 
                    onCheckedChange={(checked) => setApplyToAll(checked === true)}
                    className="checkbox-neon"
                />
                <div className="grid gap-1.5 leading-none">
                  <label
                    htmlFor="syncAll"
                    className="text-xs font-black uppercase tracking-wider leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-neon-blue"
                  >
                    Sync Entire Venue Protocol
                  </label>
                  <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-tight opacity-60 leading-normal">
                    Propagate location & status updates to all linked nodes (Published & Pending).
                  </p>
                </div>
              </div>

              {/* Linked Events */}
              <div className="space-y-4 pt-4 border-t border-neon-purple/10">
                <div className="flex items-center justify-between">
                  <Label className="text-[10px] font-bold text-neon-purple uppercase tracking-[0.2em] ml-1 flex items-center gap-2">
                    <Calendar className="w-4 h-4" />
                    Linked Signals ({allLinkedEvents.length})
                  </Label>
                  {venue?.name && (
                    <Button variant="link" size="sm" className="h-auto p-0 text-[10px] font-bold uppercase tracking-widest text-neon-purple hover:text-neon-purple/80" asChild>
                      <Link href={`/?search=${encodeURIComponent(venue.name)}`}>
                        Dashboard Trace
                        <ExternalLink className="w-3 h-3 ml-2" />
                      </Link>
                    </Button>
                  )}
                </div>
                {allLinkedEvents.length > 0 ? (
                  <div className="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto pr-2 scrollbar-neon">
                    {allLinkedEvents.map((ev) => (
                      <Link 
                        key={ev.id} 
                        href={ev.isPublished ? `/published?id=${ev.id}` : `/?id=${ev.id}`}
                        className="flex items-center justify-between p-3 rounded-xl bg-card/40 border border-border/50 group hover:border-neon-purple/40 hover:bg-neon-purple/5 transition-all duration-300"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="text-xs font-black uppercase truncate group-hover:text-neon-purple transition-colors">{ev.title}</p>
                            <Badge variant="outline" className={cn(
                                "text-[8px] h-4 px-1.5 font-black uppercase tracking-tighter",
                                ev.isPublished ? "badge-neon-green" : "badge-neon-purple"
                            )}>
                                {ev.isPublished ? 'LIVE' : 'PENDING'}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-bold uppercase tracking-widest opacity-60">
                            <span>{format(new Date(ev.start_time), 'dd MMM yyyy')}</span>
                            <span>•</span>
                            <span className="truncate">{ev.category}</span>
                          </div>
                        </div>
                        <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-neon-purple group-hover:translate-x-1 transition-all" />
                      </Link>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 rounded-xl border border-dashed border-border/50 text-center">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground opacity-50 italic">No signals linked to this node.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Location Search */}
            <div className="space-y-4 pt-4 border-t border-neon-blue/10">
              <Label className="text-[10px] font-bold text-neon-blue uppercase tracking-[0.2em] ml-1 flex items-center gap-2">
                <Search className="w-4 h-4" />
                Registry Search & Sync
              </Label>
              <div className="relative group">
                <Search className="absolute left-3.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground group-focus-within:text-neon-blue transition-colors" />
                <Input
                  placeholder="Search for physical address..."
                  value={locationSearch}
                  onChange={(e) => setLocationSearch(e.target.value)}
                  className="pl-11 bg-card/40 input-neon h-11"
                />
              </div>
              {suggestions.length > 0 && (
                <div className="border border-neon-blue/20 rounded-xl overflow-hidden bg-card/80 backdrop-blur-md shadow-2xl animate-in fade-in slide-in-from-top-2 duration-300">
                  {suggestions.map((suggestion, idx) => (
                    <button
                      key={idx}
                      className="w-full p-4 text-left hover:bg-neon-blue/10 transition-all border-b border-neon-blue/10 last:border-b-0 group"
                      onClick={() => handleLocationSelect(suggestion)}
                    >
                      <div className="font-bold text-sm text-foreground group-hover:text-neon-blue transition-colors">{suggestion.full_address}</div>
                      <div className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mt-1">{suggestion.city}, {suggestion.country_code}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Merge Venue */}
            <div className="space-y-5 pt-4 pb-8 border-t border-neon-pink/10">
              <div className="flex items-center gap-3 ml-1">
                <GitMerge className="w-5 h-5 text-neon-pink animate-pulse" />
                <Label className="text-[10px] font-bold text-neon-pink uppercase tracking-[0.2em]">
                  Merge Protocol
                </Label>
              </div>
              <p className="text-[11px] font-medium leading-relaxed text-muted-foreground bg-neon-pink/5 p-4 rounded-xl border border-neon-pink/10">
                Warning: This will decommission the current node and migrate all linked signals to a new target node. This action is final.
              </p>
              
              <div className="space-y-4">
                <Select value={targetVenueId || ''} onValueChange={setTargetVenueId}>
                    <SelectTrigger className="h-11 bg-card/40 input-neon font-bold uppercase tracking-widest text-[10px] border-neon-pink/20 focus:ring-neon-pink">
                        <SelectValue placeholder="SELECT TARGET NODE..." />
                    </SelectTrigger>
                    <SelectContent className="bg-card border-neon-pink/20">
                        {allVenues
                          .filter(v => v.id !== venue.id)
                          .map(v => (
                            <SelectItem key={v.id} value={v.id} className="text-[10px] font-bold uppercase tracking-widest">
                                {v.name} ({v.city || '??'})
                            </SelectItem>
                        ))}
                    </SelectContent>
                </Select>

                <AlertDialog>
                    <AlertDialogTrigger asChild>
                        <Button 
                            variant="neon-purple" 
                            className="w-full h-11 font-black uppercase tracking-[0.2em] border-neon-pink/30"
                            disabled={!targetVenueId || mergeMutation.isPending}
                        >
                            <GitMerge className="w-4 h-4 mr-2" />
                            {mergeMutation.isPending ? 'MIGRATING...' : 'EXECUTE MERGE'}
                        </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent className="bg-card border-neon-red/30">
                        <AlertDialogHeader>
                            <AlertDialogTitle className="text-neon-red uppercase font-black tracking-tighter">Initiate Merge Protocol?</AlertDialogTitle>
                            <AlertDialogDescription className="text-muted-foreground font-medium italic">
                                Irreversible decommissioning of &quot;{venue.name}&quot;. All child signals will be rerouted. Proceed?
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel className="bg-card border-border uppercase font-bold tracking-widest text-[10px]">Abort</AlertDialogCancel>
                            <AlertDialogAction
                                className="bg-neon-red hover:bg-neon-red/80 text-white font-black uppercase tracking-[0.2em] text-[10px]"
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
        <div className="p-6 border-t border-neon-blue/20 bg-card/90 backdrop-blur-xl sticky bottom-0 z-30 space-y-3 shadow-[0_-10px_30px_rgba(0,0,0,0.3)]">
          <Button
            variant="neon"
            className="w-full h-12 font-black uppercase tracking-[0.2em]"
            onClick={() => saveMutation.mutate(editedVenue)}
            disabled={saveMutation.isPending}
          >
            <Save className="w-5 h-5 mr-3" />
            {saveMutation.isPending ? 'SYNCING...' : 'Save Registry Changes'}
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="neon-red" className="w-full h-11 font-black uppercase tracking-[0.2em] opacity-80 hover:opacity-100">
                <Trash2 className="w-5 h-5 mr-3" />
                Delete Node
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="bg-card border-neon-red/40">
              <AlertDialogHeader>
                <AlertDialogTitle className="text-neon-red uppercase font-black tracking-tighter">Decommission Node?</AlertDialogTitle>
                <AlertDialogDescription className="text-muted-foreground font-medium">
                  Deletetion of &quot;{venue.name}&quot; will leave linked signals unrouted.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="bg-card border-border uppercase font-bold tracking-widest text-[10px]">Abort</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-neon-red hover:bg-neon-red/80 text-white font-black uppercase tracking-[0.2em] text-[10px]"
                  onClick={() => deleteMutation.mutate(venue.id)}
                >
                  Confirm Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </SheetContent>
    </Sheet>
  )
}

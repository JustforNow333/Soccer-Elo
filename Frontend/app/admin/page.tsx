"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useToast } from "@/hooks/use-toast"
import { api, type Team } from "@/lib/api"
import { AlertCircle, WifiOff } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

export default function AdminPage() {
  const [teams, setTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const { toast } = useToast()
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "unknown">("unknown")

  const [matchForm, setMatchForm] = useState({
    home_team_id: "",
    away_team_id: "",
    home_score: "",
    away_score: "",
    date: new Date().toISOString().split("T")[0],
  })

  const [teamForm, setTeamForm] = useState({
    name: "",
    country: "",
  })

  useEffect(() => {
    const fetchTeams = async () => {
      try {
        setConnectionStatus("unknown")
        const teamsData = await api.getTeams()
        setTeams(teamsData.sort((a, b) => a.name.localeCompare(b.name)))

        // Check if we got real data or mock data
        if (teamsData.length > 0 && teamsData[0].name === "Manchester City") {
          setConnectionStatus("disconnected")
          toast({
            title: "Warning",
            description: "Using sample data. Backend server not connected.",
            variant: "destructive",
          })
        } else {
          setConnectionStatus("connected")
        }
      } catch (error) {
        console.error("Failed to fetch teams:", error)
        setConnectionStatus("disconnected")
        toast({
          title: "Error",
          description: "Failed to load teams. Using sample data.",
          variant: "destructive",
        })
      } finally {
        setLoading(false)
      }
    }

    fetchTeams()
  }, [toast])

  const handleMatchSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!matchForm.home_team_id || !matchForm.away_team_id) {
      toast({
        title: "Error",
        description: "Please select both home and away teams",
        variant: "destructive",
      })
      return
    }

    if (matchForm.home_team_id === matchForm.away_team_id) {
      toast({
        title: "Error",
        description: "Home and away teams must be different",
        variant: "destructive",
      })
      return
    }

    setSubmitting(true)

    try {
      await api.createMatch({
        home_team_id: Number.parseInt(matchForm.home_team_id),
        away_team_id: Number.parseInt(matchForm.away_team_id),
        home_score: Number.parseInt(matchForm.home_score),
        away_score: Number.parseInt(matchForm.away_score),
        date: matchForm.date,
      })

      toast({
        title: "Success",
        description: "Match submitted and Elo ratings updated",
      })

      // Reset form
      setMatchForm({
        home_team_id: "",
        away_team_id: "",
        home_score: "",
        away_score: "",
        date: new Date().toISOString().split("T")[0],
      })
    } catch (error) {
      console.error("Failed to submit match:", error)
      toast({
        title: "Error",
        description: "Failed to submit match",
        variant: "destructive",
      })
    } finally {
      setSubmitting(false)
    }
  }

  const handleTeamSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!teamForm.name.trim() || !teamForm.country.trim()) {
      toast({
        title: "Error",
        description: "Please fill in both team name and country",
        variant: "destructive",
      })
      return
    }

    try {
      const newTeam = await api.createTeam(teamForm.name.trim(), teamForm.country.trim())
      setTeams((prev) => [...prev, newTeam].sort((a, b) => a.name.localeCompare(b.name)))

      toast({
        title: "Success",
        description: "Team created successfully",
      })

      // Reset form
      setTeamForm({ name: "", country: "" })
    } catch (error) {
      console.error("Failed to create team:", error)
      toast({
        title: "Error",
        description: "Failed to create team",
        variant: "destructive",
      })
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Admin Panel</h1>
          <p className="text-muted-foreground">Submit new matches and manage teams</p>
        </div>

        {connectionStatus === "disconnected" && (
          <Alert className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center gap-2">
              <WifiOff className="h-4 w-4" />
              Backend server not connected. Form submissions will use mock responses. Make sure your Flask server is
              running on http://localhost:5000
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Submit New Match</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleMatchSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="home-team">Home Team</Label>
                    <Select
                      value={matchForm.home_team_id}
                      onValueChange={(value) => setMatchForm((prev) => ({ ...prev, home_team_id: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select home team" />
                      </SelectTrigger>
                      <SelectContent>
                        {teams.map((team) => (
                          <SelectItem key={team.id} value={team.id.toString()}>
                            {team.name} ({team.country})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="away-team">Away Team</Label>
                    <Select
                      value={matchForm.away_team_id}
                      onValueChange={(value) => setMatchForm((prev) => ({ ...prev, away_team_id: value }))}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select away team" />
                      </SelectTrigger>
                      <SelectContent>
                        {teams.map((team) => (
                          <SelectItem key={team.id} value={team.id.toString()}>
                            {team.name} ({team.country})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="home-score">Home Score</Label>
                    <Input
                      id="home-score"
                      type="number"
                      min="0"
                      value={matchForm.home_score}
                      onChange={(e) => setMatchForm((prev) => ({ ...prev, home_score: e.target.value }))}
                      required
                    />
                  </div>

                  <div>
                    <Label htmlFor="away-score">Away Score</Label>
                    <Input
                      id="away-score"
                      type="number"
                      min="0"
                      value={matchForm.away_score}
                      onChange={(e) => setMatchForm((prev) => ({ ...prev, away_score: e.target.value }))}
                      required
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="match-date">Match Date</Label>
                  <Input
                    id="match-date"
                    type="date"
                    value={matchForm.date}
                    onChange={(e) => setMatchForm((prev) => ({ ...prev, date: e.target.value }))}
                    required
                  />
                </div>

                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting ? "Submitting..." : "Submit Match"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Add New Team</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleTeamSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="team-name">Team Name</Label>
                  <Input
                    id="team-name"
                    value={teamForm.name}
                    onChange={(e) => setTeamForm((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Enter team name"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="team-country">Country</Label>
                  <Input
                    id="team-country"
                    value={teamForm.country}
                    onChange={(e) => setTeamForm((prev) => ({ ...prev, country: e.target.value }))}
                    placeholder="Enter country"
                    required
                  />
                </div>

                <Button type="submit" className="w-full">
                  Add Team
                </Button>
              </form>

              <div className="mt-6">
                <h3 className="font-semibold mb-2">Current Teams ({teams.length})</h3>
                <div className="max-h-64 overflow-y-auto space-y-1">
                  {teams.map((team) => (
                    <div key={team.id} className="text-sm p-2 bg-muted rounded">
                      {team.name} ({team.country})
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

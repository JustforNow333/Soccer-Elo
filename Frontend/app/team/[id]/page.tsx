"use client"

import { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { ArrowLeft, TrendingUp, TrendingDown, Minus } from "lucide-react"
import Link from "next/link"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { api, type Team, type EloRating } from "@/lib/api"

export default function TeamDetailPage() {
  const params = useParams()
  const teamId = Number.parseInt(params.id as string)

  const [team, setTeam] = useState<Team | null>(null)
  const [eloHistory, setEloHistory] = useState<EloRating[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTeamData = async () => {
      try {
        const [teamsData, eloData] = await Promise.all([api.getTeams(), api.getEloRatings()])

        const foundTeam = teamsData.find((t) => t.id === teamId)
        setTeam(foundTeam || null)

        const teamEloHistory = eloData
          .filter((rating) => rating.team_id === teamId)
          .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

        setEloHistory(teamEloHistory)
      } catch (error) {
        console.error("Failed to fetch team data:", error)
      } finally {
        setLoading(false)
      }
    }

    if (teamId) {
      fetchTeamData()
    }
  }, [teamId])

  const chartData = eloHistory.map((rating) => ({
    date: new Date(rating.date).toLocaleDateString(),
    rating: Math.round(rating.rating),
    fullDate: rating.date,
  }))

  const getEloTrend = () => {
    if (eloHistory.length < 2) return null

    const recent = eloHistory[eloHistory.length - 1]
    const previous = eloHistory[eloHistory.length - 2]
    const change = recent.rating - previous.rating

    if (change > 0) return { direction: "up", change, icon: TrendingUp, color: "text-green-600" }
    if (change < 0) return { direction: "down", change, icon: TrendingDown, color: "text-red-600" }
    return { direction: "stable", change: 0, icon: Minus, color: "text-gray-600" }
  }

  const trend = getEloTrend()

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading team data...</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!team) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container py-8">
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4">Team Not Found</h1>
            <Link href="/">
              <Button>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Rankings
              </Button>
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />

      <div className="container py-8">
        <div className="mb-6">
          <Link href="/">
            <Button variant="outline" className="mb-4">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Rankings
            </Button>
          </Link>

          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-4xl font-bold">{team.name}</h1>
              {/* <p className="text-xl text-muted-foreground">{team.country}</p> */}
            </div>

            <div className="flex items-center gap-4">
              <Card className="p-4">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Current Elo</p>
                  <p className="text-3xl font-bold font-mono">{team.elo ? Math.round(team.elo) : "N/A"}</p>
                  {trend && (
                    <div className={`flex items-center justify-center gap-1 mt-1 ${trend.color}`}>
                      <trend.icon className="h-4 w-4" />
                      <span className="text-sm">
                        {trend.change > 0 ? "+" : ""}
                        {Math.round(trend.change)}
                      </span>
                    </div>
                  )}
                </div>
              </Card>
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-1">
          <Card>
            <CardHeader>
              <CardTitle>Elo Rating History</CardTitle>
            </CardHeader>
            <CardContent>
              {chartData.length > 0 ? (
                <ChartContainer
                  config={{
                    rating: {
                      label: "Elo Rating",
                      color: "hsl(var(--chart-1))",
                    },
                  }}
                  className="h-[400px]"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
                      <YAxis domain={["dataMin - 50", "dataMax + 50"]} tick={{ fontSize: 12 }} />
                      <ChartTooltip
                        content={<ChartTooltipContent />}
                        labelFormatter={(value, payload) => {
                          if (payload && payload[0]) {
                            return new Date(payload[0].payload.fullDate).toLocaleDateString()
                          }
                          return value
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="rating"
                        stroke="var(--color-rating)"
                        strokeWidth={2}
                        dot={{ r: 3 }}
                        activeDot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartContainer>
              ) : (
                <div className="flex items-center justify-center h-64 text-muted-foreground">
                  No Elo history available
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent Matches</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">Match history feature coming soon</div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

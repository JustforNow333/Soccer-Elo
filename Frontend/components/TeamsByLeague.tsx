"use client"

import { useMemo } from "react"
import Link from "next/link"
import { Trophy, Medal, Award } from "lucide-react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { type Team } from "@/lib/api"

interface TeamsByLeagueProps {
  teams: Team[]
  searchTerm: string
}

export function TeamsByLeague({ teams, searchTerm }: TeamsByLeagueProps) {
  const teamsByLeague = useMemo(() => {
    // Filter teams based on search term
    const filtered = teams.filter(
      (team) =>
        team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        team.league.toLowerCase().includes(searchTerm.toLowerCase())
    )

    // Group by league
    const grouped = filtered.reduce((acc, team) => {
      const league = team.league || "Unknown"
      if (!acc[league]) {
        acc[league] = []
      }
      acc[league].push(team)
      return acc
    }, {} as Record<string, Team[]>)

    // Sort teams within each league by ELO (descending)
    Object.keys(grouped).forEach(league => {
      grouped[league].sort((a, b) => (b.elo || 0) - (a.elo || 0))
    })

    // Sort leagues by highest ELO team in each league
    const leagueOrder = Object.keys(grouped).sort((a, b) => {
      const aHighest = grouped[a][0]?.elo || 0
      const bHighest = grouped[b][0]?.elo || 0
      return bHighest - aHighest
    })

    return leagueOrder.map(league => ({
      name: league,
      teams: grouped[league]
    }))
  }, [teams, searchTerm])

  const getRankIcon = (globalRank: number) => {
    if (globalRank === 1) return <Trophy className="h-4 w-4 text-yellow-500" />
    if (globalRank === 2) return <Medal className="h-4 w-4 text-gray-400" />
    if (globalRank === 3) return <Award className="h-4 w-4 text-amber-600" />
    return null
  }

  const getGlobalRank = (team: Team) => {
    // Calculate global rank based on ELO
    const sortedTeams = [...teams].sort((a, b) => (b.elo || 0) - (a.elo || 0))
    return sortedTeams.findIndex(t => t.id === team.id) + 1
  }

  return (
    <div className="space-y-6">
      {teamsByLeague.map((league) => (
        <Card key={league.name}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{league.name}</span>
              <Badge variant="secondary">{league.teams.length} teams</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">League Rank</TableHead>
                    <TableHead className="w-16">Global Rank</TableHead>
                    <TableHead>Team</TableHead>
                    <TableHead className="text-right">Elo Rating</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {league.teams.map((team, index) => {
                    const globalRank = getGlobalRank(team)
                    const isTopGlobal = globalRank <= 10
                    
                    return (
                      <TableRow
                        key={team.id}
                        className={`cursor-pointer hover:bg-muted/50 transition-colors ${
                          isTopGlobal ? "bg-primary/5" : ""
                        }`}
                      >
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            {index + 1}
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">
                          <div className="flex items-center gap-2">
                            {getRankIcon(globalRank)}
                            {globalRank}
                            {isTopGlobal && (
                              <Badge variant="secondary" className="text-xs">
                                Top 10
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Link href={`/team/${team.id}`} className="hover:underline">
                            <div className="flex items-center gap-2">
                              {team.name}
                            </div>
                          </Link>
                        </TableCell>
                        <TableCell className="text-right">
                          <span className={`font-mono ${isTopGlobal ? "text-primary font-bold" : ""}`}>
                            {team.elo ? Math.round(team.elo) : "N/A"}
                          </span>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
} 
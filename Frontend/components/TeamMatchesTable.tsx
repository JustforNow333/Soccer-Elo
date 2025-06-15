"use client"

import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import Link from "next/link"

import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

// Generate mock data for matches
function generateMatches(teamId: string, limit: number = 10) {
  const teamName = getTeamName(teamId)
  const matches = []
  const now = new Date()
  
  for (let i = 0; i < limit; i++) {
    const date = new Date(now)
    date.setDate(date.getDate() - i * 7) // One match per week
    
    const isHome = Math.random() > 0.5
    const opponentId = (parseInt(teamId) + i + 1) % 20 + 1
    const opponentName = getTeamName(opponentId.toString())
    
    // Generate a result with some bias towards the team with higher ID (assuming higher ID = better team)
    const teamStrength = parseInt(teamId)
    const opponentStrength = opponentId
    const homeAdvantage = isHome ? 2 : -2
    
    let result
    let eloChange
    
    const winProbability = (teamStrength + homeAdvantage) / (teamStrength + opponentStrength + homeAdvantage) * 0.7 + 0.15
    
    if (Math.random() < winProbability) {
      // Win
      const goals = Math.floor(Math.random() * 3) + 1
      const opponentGoals = Math.floor(Math.random() * goals)
      result = `${goals}-${opponentGoals}`
      eloChange = Math.floor(Math.random() * 10) + 5
    } else if (Math.random() < 0.5) {
      // Draw
      const goals = Math.floor(Math.random() * 3)
      result = `${goals}-${goals}`
      eloChange = Math.floor(Math.random() * 3) - 1
    } else {
      // Loss
      const opponentGoals = Math.floor(Math.random() * 3) + 1
      const goals = Math.floor(Math.random() * opponentGoals)
      result = `${goals}-${opponentGoals}`
      eloChange = -(Math.floor(Math.random() * 10) + 5)
    }
    
    matches.push({
      id: i + 1,
      date: date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
      opponent: opponentName,
      opponentId: opponentId.toString(),
      isHome,
      result,
      eloChange,
    })
  }
  
  return matches
}

// Helper function to get team name from ID
function getTeamName(id: string) {
  const teams = [
    "Manchester City", "Bayern Munich", "Real Madrid", "Liverpool", "Paris Saint-Germain",
    "Inter Milan", "Barcelona", "Manchester United", "Atletico Madrid", "Borussia Dortmund",
    "Juventus", "Chelsea", "Ajax", "RB Leipzig", "Napoli",
    "Arsenal", "Sevilla", "Benfica", "Porto", "Atalanta"
  ]
  
  return teams[parseInt(id) - 1] || "Unknown Team"
}

interface TeamMatchesTableProps {
  teamId: string
  limit?: number
}

export function TeamMatchesTable({ teamId, limit = 10 }: TeamMatchesTableProps) {
  const matches = generateMatches(teamId, limit)
  
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Opponent</TableHead>
            <TableHead className="text-center">Result</TableHead>
            <TableHead className="text-right">Elo Change</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {matches.map((match) => (
            <TableRow key={match.id}>
              <TableCell className="font-medium">{match.date}</TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  {match.isHome ? "vs" : "@"}
                  <Link 
                    href={`/teams/${match.opponentId}`} 
                    className="hover:underline"
                  >
                    {match.opponent}
                  </Link>
                </div>
              </TableCell>
              <TableCell className="text-center">
                <Badge 
                  variant={
                    match.eloChange > 0 
                      ? "success" 
                      : match.eloChange < 0 
                        ? "destructive" 
                        : "secondary"
                  }
                >
                  {match.result}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-1">
                  {match.eloChange > 0 ? (
                    <>
                      <ArrowUp className="h-4 w-4 text-green-500" />
                      <span className="text-green-500">+{match.eloChange}</span>
                    </>
                  ) : match.eloChange < 0 ? (
                    <>
                      <ArrowDown className="h-4 w-4 text-red-500" />
                      <span className="text-red-500">{match.eloChange}</span>
                    </>
                  ) : (
                    <>
                      <Minus className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">0</span>
                    </>
                  )}
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
} 
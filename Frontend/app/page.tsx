"use client"

import { useState, useEffect, useMemo } from "react"
import { Search, ChevronUp, ChevronDown, Trophy, Medal, Award } from "lucide-react"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { api, type Team } from "@/lib/api"
import { TeamsByLeague } from "@/components/TeamsByLeague"
import Link from "next/link"

// Add this after the existing imports
import { AlertCircle, Wifi, WifiOff } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

type SortField = "name" | "league" | "elo"
type SortDirection = "asc" | "desc"

export default function HomePage() {
  const [teams, setTeams] = useState<Team[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [sortField, setSortField] = useState<SortField>("elo")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")
  const [currentPage, setCurrentPage] = useState(1)
  const [activeTab, setActiveTab] = useState("overall")
  const itemsPerPage = 20

  // Add this state variable after the existing useState declarations
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "unknown">("unknown")

  // Update the fetchTeams function in the useEffect:
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        setConnectionStatus("unknown")
        const teamsData = await api.getTeams()
        setTeams(teamsData)

        // Check if we got real data or mock data
        if (teamsData.length > 0 && teamsData[0].id === 1 && teamsData[0].name === "Manchester City") {
          setConnectionStatus("disconnected")
        } else {
          setConnectionStatus("connected")
        }
      } catch (error) {
        console.error("Failed to fetch teams:", error)
        setConnectionStatus("disconnected")
      } finally {
        setLoading(false)
      }
    }

    fetchTeams()
  }, [])

  const filteredAndSortedTeams = useMemo(() => {
    const filtered = teams.filter(
      (team) =>
        team.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        team.league.toLowerCase().includes(searchTerm.toLowerCase()),
    )

    filtered.sort((a, b) => {
      let aValue: string | number
      let bValue: string | number

      switch (sortField) {
        case "name":
          aValue = a.name
          bValue = b.name
          break
        case "league":
          aValue = a.league
          bValue = b.league
          break
        case "elo":
          aValue = a.elo || 0
          bValue = b.elo || 0
          break
        default:
          return 0
      }

      if (typeof aValue === "string" && typeof bValue === "string") {
        return sortDirection === "asc" ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue)
      }

      return sortDirection === "asc" ? (aValue as number) - (bValue as number) : (bValue as number) - (aValue as number)
    })

    return filtered
  }, [teams, searchTerm, sortField, sortDirection])

  const paginatedTeams = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    return filteredAndSortedTeams.slice(startIndex, startIndex + itemsPerPage)
  }, [filteredAndSortedTeams, currentPage])

  const totalPages = Math.ceil(filteredAndSortedTeams.length / itemsPerPage)

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortDirection("desc")
    }
    setCurrentPage(1)
  }

  const getRankIcon = (index: number) => {
    const rank = (currentPage - 1) * itemsPerPage + index + 1
    if (rank === 1) return <Trophy className="h-4 w-4 text-yellow-500" />
    if (rank === 2) return <Medal className="h-4 w-4 text-gray-400" />
    if (rank === 3) return <Award className="h-4 w-4 text-amber-600" />
    return null
  }

  const isTopTen = (index: number) => {
    const rank = (currentPage - 1) * itemsPerPage + index + 1
    return rank <= 10
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="container py-8">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading teams...</p>
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
          <h1 className="text-4xl font-bold mb-2 neon-glow">Global Soccer Elo Rankings</h1>
          <p className="text-muted-foreground">Track and compare soccer team ratings from around the world</p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Search Teams
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Input
              placeholder="Search by team name or league..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1)
              }}
              className="max-w-md"
            />
          </CardContent>
        </Card>

        {connectionStatus === "disconnected" && (
          <Alert className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center gap-2">
              <WifiOff className="h-4 w-4" />
              Unable to connect to the backend server. Showing sample data. Make sure your Flask server is running on
              http://localhost:5000
            </AlertDescription>
          </Alert>
        )}

        {connectionStatus === "connected" && (
          <Alert className="mb-6 border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200">
            <AlertDescription className="flex items-center gap-2">
              <Wifi className="h-4 w-4" />
              Connected to backend server
            </AlertDescription>
          </Alert>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="overall">Overall Rankings</TabsTrigger>
            <TabsTrigger value="by-league">By League</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overall">
            <Card>
              <CardHeader>
                <CardTitle>Overall Team Rankings</CardTitle>
                <p className="text-sm text-muted-foreground">Showing {filteredAndSortedTeams.length} teams</p>
              </CardHeader>
              <CardContent>
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-16">Rank</TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort("name")}
                        className="h-auto p-0 font-semibold hover:bg-transparent"
                      >
                        Team
                        {sortField === "name" &&
                          (sortDirection === "asc" ? (
                            <ChevronUp className="ml-1 h-4 w-4" />
                          ) : (
                            <ChevronDown className="ml-1 h-4 w-4" />
                          ))}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort("league")}
                        className="h-auto p-0 font-semibold hover:bg-transparent"
                      >
                        League
                        {sortField === "league" &&
                          (sortDirection === "asc" ? (
                            <ChevronUp className="ml-1 h-4 w-4" />
                          ) : (
                            <ChevronDown className="ml-1 h-4 w-4" />
                          ))}
                      </Button>
                    </TableHead>
                    <TableHead>
                      <Button
                        variant="ghost"
                        onClick={() => handleSort("elo")}
                        className="h-auto p-0 font-semibold hover:bg-transparent"
                      >
                        Elo Rating
                        {sortField === "elo" &&
                          (sortDirection === "asc" ? (
                            <ChevronUp className="ml-1 h-4 w-4" />
                          ) : (
                            <ChevronDown className="ml-1 h-4 w-4" />
                          ))}
                      </Button>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedTeams.map((team, index) => (
                    <TableRow
                      key={team.id}
                      className={`cursor-pointer hover:bg-muted/50 transition-colors ${
                        isTopTen(index) ? "bg-primary/5" : ""
                      }`}
                    >
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          {getRankIcon(index)}
                          {(currentPage - 1) * itemsPerPage + index + 1}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Link href={`/team/${team.id}`} className="hover:underline">
                          <div className="flex items-center gap-2">
                            {team.name}
                            {isTopTen(index) && (
                              <Badge variant="secondary" className="text-xs">
                                Top 10
                              </Badge>
                            )}
                          </div>
                        </Link>
                      </TableCell>
                      <TableCell>{team.league}</TableCell>
                      <TableCell>
                        <span className="font-mono">{team.elo ? Math.round(team.elo) : "N/A"}</span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-6">
                <p className="text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="by-league">
            <TeamsByLeague teams={teams} searchTerm={searchTerm} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

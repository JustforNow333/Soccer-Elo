"use client";

import { useState, useEffect } from "react"
import { ArrowDown, ArrowUp, ArrowUpDown, Trophy } from 'lucide-react'
import Link from "next/link"

import { Button } from "@/components/ui/button"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"

type SortDirection = "asc" | "desc" | null
type SortField = "name" | "league" | "elo" | null

export function TeamTable() {
  const [currentPage, setCurrentPage] = useState(1)
  const [sortField, setSortField] = useState<SortField>("elo")
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc")
  const [teams, setTeams] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const teamsPerPage = 10
  const totalPages = Math.ceil(teams.length / teamsPerPage)
  
  useEffect(() => {
    const fetchTeams = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const teamsData = await api.getTeams()
        setTeams(teamsData)
        console.log(`Successfully loaded ${teamsData.length} teams`)
      } catch (err) {
        console.error("Failed to fetch teams:", err)
        setError("Failed to load teams")
      } finally {
        setLoading(false)
      }
    }

    fetchTeams()
  }, [])
  
  
  // Sort teams based on current sort field and direction
  const sortedTeams = [...teams].sort((a, b) => {
    if (!sortField) return 0
    
    if (sortField === "elo") {
      const aElo = a.elo !== undefined && a.elo !== null ? a.elo : 0
      const bElo = b.elo !== undefined && b.elo !== null ? b.elo : 0
      return sortDirection === "asc" ? aElo - bElo : bElo - aElo
    }
    
    const aValue = a[sortField] || ""
    const bValue = b[sortField] || ""
    
    if (sortDirection === "asc") {
      return aValue.toString().localeCompare(bValue.toString())
    } else {
      return bValue.toString().localeCompare(aValue.toString())
    }
  })
  
  // Get current page teams
  const currentTeams = sortedTeams.slice(
    (currentPage - 1) * teamsPerPage,
    currentPage * teamsPerPage
  )
  
  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      const nextDir = sortDirection === "asc" ? "desc" : sortDirection === "desc" ? null : "asc"
      setSortDirection(nextDir)
      if (nextDir === null) {
        setSortField("elo") // default back to elo
        setSortDirection("desc")
      }
    } else {
      setSortField(field)
      setSortDirection("asc")
    }
  }
  
  // Get sort icon
  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="ml-2 h-4 w-4" />
    if (sortDirection === "asc") return <ArrowUp className="ml-2 h-4 w-4" />
    if (sortDirection === "desc") return <ArrowDown className="ml-2 h-4 w-4" />
    return <ArrowUpDown className="ml-2 h-4 w-4" />
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading teams...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  if (teams.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">No teams found</div>
      </div>
    )
  }

  return (
    <div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12 text-center">#</TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  onClick={() => handleSort("name")}
                  className="flex items-center px-0 font-medium"
                >
                  Team {getSortIcon("name")}
                </Button>
              </TableHead>
              <TableHead>
                <Button
                  variant="ghost"
                  onClick={() => handleSort("league")}
                  className="flex items-center px-0 font-medium"
                >
                  League {getSortIcon("league")}
                </Button>
              </TableHead>
              <TableHead className="text-right">
                <Button
                  variant="ghost"
                  onClick={() => handleSort("elo")}
                  className="flex items-center justify-end px-0 font-medium"
                >
                  Elo Rating {getSortIcon("elo")}
                </Button>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {currentTeams.map((team, index) => {
              const actualRank = (currentPage - 1) * teamsPerPage + index + 1
              const isTopTen = actualRank <= 10
              
              return (
                <TableRow key={team.id || `team-${index}`} className="group">
                  <TableCell className="text-center font-medium">
                    {isTopTen ? (
                      <div className="flex justify-center">
                        <Badge variant="secondary" className="flex items-center gap-1 px-1.5">
                          {actualRank}
                          <Trophy className="h-3 w-3 text-amber-500" />
                        </Badge>
                      </div>
                    ) : (
                      actualRank
                    )}
                  </TableCell>
                  <TableCell>
                    <Link 
                      href={team.id ? `/teams/${team.id}` : "#"} 
                      className="font-medium text-primary hover:underline"
                    >
                      {team.name || "Unknown Team"}
                    </Link>
                  </TableCell>
                  <TableCell>{team.league || "Unknown"}</TableCell>
                  <TableCell className="text-right font-medium">
                    <span className={isTopTen ? "text-primary" : ""}>
                      {team.elo !== undefined && team.elo !== null ? team.elo.toLocaleString() : "N/A"}
                    </span>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-center py-4">
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious 
                href="#" 
                onClick={(e) => {
                  e.preventDefault()
                  if (currentPage > 1) setCurrentPage(currentPage - 1)
                }}
                className={currentPage === 1 ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
            {Array.from({ length: totalPages }).map((_, i) => {
              const page = i + 1
              // Show first page, last page, and pages around current page
              if (
                page === 1 ||
                page === totalPages ||
                (page >= currentPage - 1 && page <= currentPage + 1)
              ) {
                return (
                  <PaginationItem key={page}>
                    <PaginationLink
                      href="#"
                      onClick={(e) => {
                        e.preventDefault()
                        setCurrentPage(page)
                      }}
                      isActive={page === currentPage}
                    >
                      {page}
                    </PaginationLink>
                  </PaginationItem>
                )
              }
              
              // Show ellipsis for gaps
              if (page === 2 || page === totalPages - 1) {
                return (
                  <PaginationItem key={page}>
                    <PaginationEllipsis />
                  </PaginationItem>
                )
              }
              
              return null
            })}
            <PaginationItem>
              <PaginationNext 
                href="#" 
                onClick={(e) => {
                  e.preventDefault()
                  if (currentPage < totalPages) setCurrentPage(currentPage + 1)
                }}
                className={currentPage === totalPages ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      </div>
    </div>
  )
}

// Check if we're running on the server (SSR) or client
const getBaseUrl = () => {
  // Use environment variable if available, otherwise fallback
  const envUrl = process.env.NEXT_PUBLIC_API_URL
  if (envUrl) {
    return envUrl
  }
  
  if (typeof window === 'undefined') {
    // Server-side: use localhost for API calls during SSR
    return 'http://localhost:5000/api'
  }
  // Client-side: use relative URL which gets proxied by Next.js
  return 'http://localhost:5000/api'
}

const API_BASE_URL = getBaseUrl()
console.log("Resolved API_BASE_URL:", API_BASE_URL)

export interface Team {
  id: number
  name: string
  league: string
  elo: number | null
}

export interface Match {
  id: number
  date: string
  home_team: {
    id: number
    name: string
    country: string
  }
  away_team: {
    id: number
    name: string
    country: string
  }
  home_score: number
  away_score: number
}

export interface EloRating {
  team_id: number
  rating: number
  date: string
}

// Mock data for development/fallback
const mockTeams: Team[] = [
  { id: 1, name: "Manchester City", league: "Premier League", elo: 2100 },
  { id: 2, name: "Bayern Munich", league: "Bundesliga", elo: 2080 },
  { id: 3, name: "Real Madrid", league: "La Liga", elo: 2070 },
  { id: 4, name: "Barcelona", league: "La Liga", elo: 2050 },
  { id: 5, name: "Liverpool", league: "Premier League", elo: 2040 },
  { id: 6, name: "PSG", league: "Ligue 1", elo: 2030 },
  { id: 7, name: "Chelsea", league: "Premier League", elo: 2020 },
  { id: 8, name: "Juventus", league: "Serie A", elo: 2010 },
  { id: 9, name: "Arsenal", league: "Premier League", elo: 2000 },
  { id: 10, name: "AC Milan", league: "Serie A", elo: 1990 },
]

const mockEloRatings: EloRating[] = [
  { team_id: 1, rating: 2000, date: "2024-01-01" },
  { team_id: 1, rating: 2050, date: "2024-02-01" },
  { team_id: 1, rating: 2100, date: "2024-03-01" },
  { team_id: 2, rating: 1980, date: "2024-01-01" },
  { team_id: 2, rating: 2030, date: "2024-02-01" },
  { team_id: 2, rating: 2080, date: "2024-03-01" },
]

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = 105000): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    clearTimeout(timeoutId)
    return response
  } catch (error) {
    clearTimeout(timeoutId)
    throw error
  }
}

export const api = {
  async getTeams(): Promise<Team[]> {
    try {
      console.log(`Fetching teams from: ${API_BASE_URL}/teams/`)
      const response = await fetchWithTimeout(`${API_BASE_URL}/teams/`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("Teams data received:", data)
      return data.teams || []
    } catch (error) {
      console.error("API Error fetching teams:", error)
      console.log("Using mock data as fallback")
      return mockTeams
    }
  },

  async createTeam(name: string, league: string): Promise<Team> {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/teams/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, league }),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error("API Error creating team:", error)
      // Return a mock team for development
      const mockTeam: Team = {
        id: Date.now(),
        name,
        league,
        elo: 1000,
      }
      return mockTeam
    }
  },

  async createMatch(matchData: {
    home_team_id: number
    away_team_id: number
    home_score: number
    away_score: number
    date: string
  }): Promise<{ id: number }> {
    try {
      const response = await fetchWithTimeout(`${API_BASE_URL}/matches/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(matchData),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error("API Error creating match:", error)
      // Return a mock response for development
      return { id: Date.now() }
    }
  },

  async getEloRatings(): Promise<EloRating[]> {
    try {
      console.log(`Fetching elo ratings from: ${API_BASE_URL}/elo-ratings/`)
      const response = await fetchWithTimeout(`${API_BASE_URL}/elo-ratings/`)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log("Elo ratings data received:", data)
      return data.elo_ratings || []
    } catch (error) {
      console.error("API Error fetching elo ratings:", error)
      console.log("Using mock elo data as fallback")
      return mockEloRatings
    }
  },
}

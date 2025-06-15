"use client"

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

// Generate mock data for the Elo history chart
function generateEloHistory(teamId: string) {
  // Base Elo rating based on team ID
  const baseElo = 1900 + parseInt(teamId) * 50
  
  // Generate data for the last 12 months
  const data = []
  const now = new Date()
  
  for (let i = 11; i >= 0; i--) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1)
    
    // Create some variation in the Elo rating
    const variation = Math.sin(i / 3) * 30 + (Math.random() - 0.5) * 20
    const elo = Math.round(baseElo + variation)
    
    data.push({
      date: date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
      elo: elo,
    })
  }
  
  return data
}

interface TeamEloChartProps {
  teamId: string
}

export function TeamEloChart({ teamId }: TeamEloChartProps) {
  const data = generateEloHistory(teamId)
  
  // Calculate min and max for the y-axis
  const minElo = Math.min(...data.map(d => d.elo)) - 20
  const maxElo = Math.max(...data.map(d => d.elo)) + 20
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart
        data={data}
        margin={{
          top: 5,
          right: 10,
          left: 10,
          bottom: 0,
        }}
      >
        <XAxis
          dataKey="date"
          stroke="#888888"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#888888"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          domain={[minElo, maxElo]}
          tickFormatter={(value) => `${value}`}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (active && payload && payload.length) {
              return (
                <div className="rounded-lg border bg-background p-2 shadow-sm">
                  <div className="grid grid-cols-2 gap-2">
                    <div className="flex flex-col">
                      <span className="text-[0.70rem] uppercase text-muted-foreground">
                        Date
                      </span>
                      <span className="font-bold text-muted-foreground">
                        {payload[0].payload.date}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[0.70rem] uppercase text-muted-foreground">
                        Elo
                      </span>
                      <span className="font-bold">{payload[0].value}</span>
                    </div>
                  </div>
                </div>
              )
            }
            
            return null
          }}
        />
        <Line
          type="monotone"
          dataKey="elo"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          activeDot={{
            r: 6,
            style: { fill: "hsl(var(--primary))", opacity: 0.8 },
          }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

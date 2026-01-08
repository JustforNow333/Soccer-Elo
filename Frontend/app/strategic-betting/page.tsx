"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/hooks/use-toast"
import { TrendingUp, Target, Crown, Calendar, Users, AlertCircle, Shield, Settings, AlertTriangle, X } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface BettingOpportunity {
  match_id: number
  date: string
  home_team: {
    id: number
    name: string
    league: string
    elo: number
  }
  away_team: {
    id: number
    name: string
    league: string
    elo: number
  }
  favored_team: {
    id: number
    name: string
    elo: number
  }
  underdog_team: {
    id: number
    name: string
    elo: number
  }
  elo_difference: number
  win_probability: number
  category: string
  confidence_level: string
  betting_recommendation: string
}

interface BettingData {
  opportunities: BettingOpportunity[]
  total_count: number
  categories: {
    good_chance: number
    great_chance: number
    almost_certain: number
  }
}

export default function StrategicBettingPage() {
  const [email, setEmail] = useState("")
  const [bettingData, setBettingData] = useState<BettingData | null>(null)
  const [loading, setLoading] = useState(false)
  const [hasAccess, setHasAccess] = useState(false)
  const [showSubscriptionManagement, setShowSubscriptionManagement] = useState(false)
  const [subscriptionStatus, setSubscriptionStatus] = useState<any>(null)
  const [cancelLoading, setCancelLoading] = useState(false)
  const { toast } = useToast()

  const checkPremiumAndLoadData = async () => {
    if (!email || !email.includes("@")) {
      toast({
        title: "Error",
        description: "Please enter a valid email address",
        variant: "destructive",
      })
      return
    }

    setLoading(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) {
        throw new Error("API URL not configured. Please contact support.")
      }
      
      // Check premium status first
      const premiumResponse = await fetch(`${apiUrl}/user/premium-status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      })

      const premiumData = await premiumResponse.json()

      if (!premiumData.has_premium) {
        toast({
          title: "Premium Required",
          description: "This feature requires a premium subscription",
          variant: "destructive",
        })
        return
      }

      setHasAccess(true)

      // Get betting opportunities
      const bettingResponse = await fetch(`${apiUrl}/strategic-betting`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      })

      const bettingResult = await bettingResponse.json()

      if (!bettingResponse.ok) {
        throw new Error(bettingResult.error || "Failed to load betting data")
      }

      setBettingData(bettingResult)
      
      toast({
        title: "Success",
        description: `Found ${bettingResult.total_count} betting opportunities`,
      })
    } catch (error) {
      console.error("Error:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to load data",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const getCategoryBadgeColor = (category: string) => {
    switch (category) {
      case "good_chance":
        return "bg-blue-100 text-blue-800"
      case "great_chance":
        return "bg-orange-100 text-orange-800"
      case "almost_certain":
        return "bg-green-100 text-green-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "good_chance":
        return <TrendingUp className="h-4 w-4" />
      case "great_chance":
        return <Target className="h-4 w-4" />
      case "almost_certain":
        return <Crown className="h-4 w-4" />
      default:
        return null
    }
  }

  const getSubscriptionStatus = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) {
        throw new Error("API URL not configured")
      }

      const response = await fetch(`${apiUrl}/subscription-status`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to get subscription status")
      }

      setSubscriptionStatus(data)
      setShowSubscriptionManagement(true)
    } catch (error) {
      console.error("Error getting subscription status:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to get subscription status",
        variant: "destructive",
      })
    }
  }

  const cancelSubscription = async () => {
    if (!confirm("Are you sure you want to cancel your subscription? You'll lose access to premium features at the end of your current billing period.")) {
      return
    }

    setCancelLoading(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL
      if (!apiUrl) {
        throw new Error("API URL not configured")
      }

      const response = await fetch(`${apiUrl}/cancel-subscription`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || "Failed to cancel subscription")
      }

      toast({
        title: "Subscription Canceled",
        description: "Your subscription has been canceled. You'll continue to have access until the end of your current billing period.",
      })

      // Refresh subscription status
      await getSubscriptionStatus()
    } catch (error) {
      console.error("Error canceling subscription:", error)
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to cancel subscription",
        variant: "destructive",
      })
    } finally {
      setCancelLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <div className="container py-8 max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <div className="flex justify-center items-center gap-2 mb-4">
            <Shield className="h-8 w-8 text-primary" />
            <Crown className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-4xl font-bold mb-2">Strategic Betting Insights</h1>
          <p className="text-muted-foreground text-lg">
            Data-driven betting opportunities based on Elo rating analysis
          </p>
        </div>

        {/* Access Form */}
        {!hasAccess && (
          <Card className="mb-8 max-w-md mx-auto">
            <CardHeader>
              <CardTitle className="text-center">Access Premium Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="email">Email Address</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={loading}
                  />
                </div>
                <Button 
                  onClick={checkPremiumAndLoadData}
                  className="w-full" 
                  disabled={loading || !email}
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Loading...
                    </>
                  ) : (
                    <>
                      <Shield className="h-4 w-4 mr-2" />
                      Access Betting Insights
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Betting Data Display */}
        {hasAccess && bettingData && (
          <>
            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-4 mb-8">
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Total Opportunities</p>
                      <p className="text-2xl font-bold">{bettingData.total_count}</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Good Chance</p>
                      <p className="text-2xl font-bold text-blue-600">{bettingData.categories.good_chance}</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-blue-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Great Chance</p>
                      <p className="text-2xl font-bold text-orange-600">{bettingData.categories.great_chance}</p>
                    </div>
                    <Target className="h-8 w-8 text-orange-600" />
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Almost Certain</p>
                      <p className="text-2xl font-bold text-green-600">{bettingData.categories.almost_certain}</p>
                    </div>
                    <Crown className="h-8 w-8 text-green-600" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Subscription Management */}
            <Card className="mb-8">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Settings className="h-5 w-5" />
                    Subscription Management
                  </CardTitle>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={getSubscriptionStatus}
                  >
                    <Settings className="h-4 w-4 mr-2" />
                    Manage Subscription
                  </Button>
                </div>
              </CardHeader>
              {showSubscriptionManagement && subscriptionStatus && (
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
                      <div>
                        <p className="font-medium">Subscription Status</p>
                        <p className="text-sm text-muted-foreground">
                          Current status: <span className="font-medium capitalize">{subscriptionStatus.user.subscription_status}</span>
                        </p>
                        {subscriptionStatus.user.subscription_start_date && (
                          <p className="text-sm text-muted-foreground">
                            Started: {new Date(subscriptionStatus.user.subscription_start_date).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <div className="text-right">
                        <Badge variant={subscriptionStatus.user.subscription_status === 'active' ? 'default' : 'secondary'}>
                          {subscriptionStatus.user.subscription_status === 'active' ? 'Active' : 'Inactive'}
                        </Badge>
                      </div>
                    </div>
                    
                    {subscriptionStatus.user.subscription_status === 'active' && (
                      <Alert>
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription>
                          <div className="space-y-2">
                            <p>Want to cancel your subscription?</p>
                            <Button 
                              variant="destructive" 
                              size="sm"
                              onClick={cancelSubscription}
                              disabled={cancelLoading}
                            >
                              {cancelLoading ? (
                                <>
                                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                  Canceling...
                                </>
                              ) : (
                                <>
                                  <X className="h-4 w-4 mr-2" />
                                  Cancel Subscription
                                </>
                              )}
                            </Button>
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}
                    
                    {subscriptionStatus.user.subscription_status === 'canceled' && (
                      <Alert>
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>
                          <div className="space-y-2">
                            <p>Your subscription has been canceled.</p>
                            {subscriptionStatus.user.subscription_end_date && (
                              <p className="text-sm">
                                Access will end on: {new Date(subscriptionStatus.user.subscription_end_date).toLocaleDateString()}
                              </p>
                            )}
                          </div>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </CardContent>
              )}
            </Card>

            {/* Betting Opportunities */}
            {bettingData.opportunities.length > 0 ? (
              <div className="space-y-4">
                <h2 className="text-2xl font-bold mb-4">Betting Opportunities</h2>
                {bettingData.opportunities.map((opportunity) => (
                  <Card key={opportunity.match_id} className="hover:shadow-lg transition-shadow">
                    <CardContent className="p-6">
                      <div className="grid gap-4 md:grid-cols-4">
                        {/* Match Info */}
                        <div className="md:col-span-2">
                          <div className="flex items-center gap-2 mb-2">
                            <Calendar className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm text-muted-foreground">
                              {new Date(opportunity.date).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-medium">{opportunity.home_team.name}</span>
                              <Badge variant="outline">{opportunity.home_team.elo}</Badge>
                            </div>
                            <div className="text-center text-sm text-muted-foreground">vs</div>
                            <div className="flex items-center justify-between">
                              <span className="font-medium">{opportunity.away_team.name}</span>
                              <Badge variant="outline">{opportunity.away_team.elo}</Badge>
                            </div>
                          </div>
                        </div>

                        {/* Analysis */}
                        <div>
                          <Badge 
                            className={`mb-2 ${getCategoryBadgeColor(opportunity.category)}`}
                          >
                            <span className="flex items-center gap-1">
                              {getCategoryIcon(opportunity.category)}
                              {opportunity.confidence_level}
                            </span>
                          </Badge>
                          <div className="space-y-1 text-sm">
                            <div>
                              <span className="text-muted-foreground">Favored: </span>
                              <span className="font-medium">{opportunity.favored_team.name}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Win Probability: </span>
                              <span className="font-bold">{opportunity.win_probability}%</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Elo Difference: </span>
                              <span className="font-medium">{opportunity.elo_difference}</span>
                            </div>
                          </div>
                        </div>

                        {/* Recommendation */}
                        <div className="flex items-center">
                          <Alert className="w-full">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription className="text-sm">
                              {opportunity.betting_recommendation}
                            </AlertDescription>
                          </Alert>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="p-8 text-center">
                  <Users className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold mb-2">No Opportunities Found</h3>
                  <p className="text-muted-foreground">
                    No upcoming matches meet the strategic betting criteria at this time.
                  </p>
                </CardContent>
              </Card>
            )}
          </>
        )}

        {/* Legend */}
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Betting Categories Explained</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex items-start gap-3">
                <TrendingUp className="h-5 w-5 text-blue-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-blue-600">Good Chance</h4>
                  <p className="text-sm text-muted-foreground">
                    191-239 Elo difference. Solid betting opportunities with good probability.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Target className="h-5 w-5 text-orange-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-orange-600">Great Chance</h4>
                  <p className="text-sm text-muted-foreground">
                    250-399 Elo difference. High-confidence betting opportunities.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <Crown className="h-5 w-5 text-green-600 mt-1" />
                <div>
                  <h4 className="font-semibold text-green-600">Almost Certain</h4>
                  <p className="text-sm text-muted-foreground">
                    400+ Elo difference. Extremely high-confidence opportunities.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
} 
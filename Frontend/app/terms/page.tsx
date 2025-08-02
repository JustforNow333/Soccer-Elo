import { Header } from "@/components/header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <div className="container py-8 max-w-4xl">
        <Card>
          <CardHeader>
            <CardTitle className="text-3xl font-bold">Terms of Service</CardTitle>
            <p className="text-muted-foreground">Effective Date: August 2, 2025</p>
          </CardHeader>
          <CardContent className="prose prose-gray dark:prose-invert max-w-none">
            <p className="text-base leading-relaxed mb-6">
              Welcome to our Soccer Elo Ratings site. By accessing or using our services, you agree to the following terms and conditions:
            </p>

            <div className="space-y-6">
              <section>
                <h2 className="text-xl font-semibold mb-3">1. Account Usage</h2>
                <p className="text-base leading-relaxed">
                  Accounts are intended for use by a single individual. Sharing your account with others is strictly prohibited. We reserve the right to suspend or terminate accounts that show evidence of account sharing, including but not limited to logins from multiple devices, IPs, or geographic regions.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold mb-3">2. Data Accuracy</h2>
                <p className="text-base leading-relaxed">
                  While we strive to ensure all Elo ratings and match data are accurate and current, we do not guarantee the correctness, completeness, or reliability of any data on the site.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold mb-3">3. Fair Use</h2>
                <p className="text-base leading-relaxed">
                  You agree not to misuse or overburden our servers, including excessive API calls, scraping, or automated access beyond normal use. We may block or restrict access at our discretion to maintain the integrity and performance of the platform.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold mb-3">4. Intellectual Property</h2>
                <p className="text-base leading-relaxed">
                  All content, including but not limited to Elo rating logic, design elements, logos, and original text, is the property of the site's creators unless otherwise noted. You may not reproduce or distribute content without express permission.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold mb-3">5. Privacy</h2>
                <p className="text-base leading-relaxed">
                  We collect limited information (such as IP address and browser information) for security, analytics, and fraud prevention purposes. We do not sell or share your data with third parties except as required by law.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold mb-3">6. Termination</h2>
                <p className="text-base leading-relaxed">
                  We reserve the right to terminate or restrict your access to the site at any time, for any reason, including violations of these terms.
                </p>
              </section>

              <section>
                <h2 className="text-xl font-semibold mb-3">7. Changes to the Terms</h2>
                <p className="text-base leading-relaxed">
                  These terms may be updated at any time. Continued use of the site after changes are posted constitutes your acceptance of the updated terms.
                </p>
              </section>

              <section>
                <p className="text-base leading-relaxed">
                  If you have any questions about these terms, feel free to contact us through the appropriate channels on the site.
                </p>
              </section>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
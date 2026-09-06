import { useEffect, useState } from 'react'
import { Bot, CheckCircle, XCircle, AlertTriangle, RefreshCw, Shield, Zap, TrendingUp, History, Activity, ArrowUpRight, ArrowDownRight, DollarSign, Flame, Sparkles } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { showToast } from '@/utils/toast'

interface LumibotEval {
  status: string
  win_rate: number
  sharpe_ratio: number
  max_drawdown: number
  profit_factor: number
  engine: string
}

interface Signal {
  symbol: string
  name?: string
  badge_type?: string
  price: number
  change_percent?: number
  action: string
  position_type?: string
  quantity: number
  rsi?: number
  confidence?: number
  stop_loss?: number
  target_price?: number
  reason: string
  exchange: string
  lumibot?: LumibotEval
}

interface PendingTrade {
  trade_id: string
  symbol: string
  action: string
  position_type?: string
  quantity: number
  price: number
  total_usd: number
  reason: string
}

interface HistoryRecord {
  trade_id: string
  symbol: string
  action: string
  position_type?: string
  quantity: number
  price: number
  status: string
  timestamp: string
}

export default function AIAgentDashboard() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [pendingApprovals, setPendingApprovals] = useState<PendingTrade[]>([])
  const [history, setHistory] = useState<HistoryRecord[]>([])
  const [thresholdUsd, setThresholdUsd] = useState<number>(200)
  const [activePreset, setActivePreset] = useState<string>('all')
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isScanning, setIsScanning] = useState<boolean>(false)
  const [isProcessing, setIsProcessing] = useState<string | null>(null)

  const fetchStatus = async (preset: string = activePreset) => {
    try {
      setIsLoading(true)
      const res = await fetch(`/api/v1/ai-agent/status?preset=${preset}`)
      if (res.ok) {
        const data = await res.json()
        setSignals(data.signals || [])
        setPendingApprovals(data.pending_approvals || [])
        setHistory(data.execution_history || [])
        setThresholdUsd(data.threshold_usd || 200)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setIsLoading(false)
    }
  }

  const triggerScan = async (preset: string = activePreset) => {
    try {
      setIsScanning(true)
      const res = await fetch('/api/v1/ai-agent/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ preset })
      })
      if (res.ok) {
        const data = await res.json()
        setSignals(data.signals || [])
        showToast.success(data.message || 'Market scan completed!', 'system')
      }
    } catch (e) {
      showToast.error('Market scan failed', 'system')
    } finally {
      setIsScanning(false)
    }
  }

  const handlePresetChange = (newPreset: string) => {
    setActivePreset(newPreset)
    fetchStatus(newPreset)
  }

  useEffect(() => {
    fetchStatus(activePreset)
    const interval = setInterval(() => fetchStatus(activePreset), 10000)
    return () => clearInterval(interval)
  }, [activePreset])

  const handleApproval = async (tradeId: string, action: 'approve' | 'reject') => {
    try {
      setIsProcessing(tradeId)
      const res = await fetch('/api/v1/ai-agent/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trade_id: tradeId, action }),
      })
      if (res.ok) {
        showToast.success(
          action === 'approve' ? `Trade ${tradeId} Approved & Executed!` : `Trade ${tradeId} Rejected`,
          'system'
        )
        fetchStatus(activePreset)
      } else {
        showToast.error(`Failed to process trade ${tradeId}`, 'system')
      }
    } catch (e) {
      showToast.error('Network error processing trade', 'system')
    } finally {
      setIsProcessing(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-pink-500/10 text-pink-500 border border-pink-500/20">
              <Bot className="w-8 h-8" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">AI Agent & Lumibot Market Engine</h1>
              <p className="text-muted-foreground">
                Dynamic US Stock/ETF Scanner, Top Gainers of the Day, Cheap High-Yield ETFs & Lumibot Validation
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="default"
            size="sm"
            className="bg-pink-600 hover:bg-pink-700 text-white font-semibold shadow-lg shadow-pink-500/20"
            onClick={() => triggerScan(activePreset)}
            disabled={isScanning}
          >
            <Activity className={`w-4 h-4 mr-2 ${isScanning ? 'animate-spin' : ''}`} />
            {isScanning ? 'Scanning US Market...' : 'Scan Market Now'}
          </Button>

          <Button variant="outline" size="sm" onClick={() => fetchStatus(activePreset)} disabled={isLoading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Preset Filter Pills */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-xl bg-card border">
        <Button
          size="sm"
          variant={activePreset === 'all' ? 'default' : 'ghost'}
          className={activePreset === 'all' ? 'bg-pink-600 hover:bg-pink-700 text-white font-semibold' : ''}
          onClick={() => handlePresetChange('all')}
        >
          <Flame className="w-4 h-4 mr-1.5 text-orange-400" />
          All Markets
        </Button>

        <Button
          size="sm"
          variant={activePreset === 'cheap' ? 'default' : 'ghost'}
          className={activePreset === 'cheap' ? 'bg-emerald-600 hover:bg-emerald-700 text-white font-semibold' : ''}
          onClick={() => handlePresetChange('cheap')}
        >
          <DollarSign className="w-4 h-4 mr-1.5 text-emerald-400" />
          Cheap ETFs (&lt; $60)
        </Button>

        <Button
          size="sm"
          variant={activePreset === 'etf' ? 'default' : 'ghost'}
          className={activePreset === 'etf' ? 'bg-indigo-600 hover:bg-indigo-700 text-white font-semibold' : ''}
          onClick={() => handlePresetChange('etf')}
        >
          <Sparkles className="w-4 h-4 mr-1.5 text-indigo-400" />
          All Performing ETFs
        </Button>

        <Button
          size="sm"
          variant={activePreset === 'gainers' ? 'default' : 'ghost'}
          className={activePreset === 'gainers' ? 'bg-blue-600 hover:bg-blue-700 text-white font-semibold' : ''}
          onClick={() => handlePresetChange('gainers')}
        >
          <TrendingUp className="w-4 h-4 mr-1.5 text-blue-400" />
          Top Gainers of Day
        </Button>

        <Button
          size="sm"
          variant={activePreset === 'leveraged' ? 'default' : 'ghost'}
          className={activePreset === 'leveraged' ? 'bg-purple-600 hover:bg-purple-700 text-white font-semibold' : ''}
          onClick={() => handlePresetChange('leveraged')}
        >
          <Zap className="w-4 h-4 mr-1.5 text-purple-400" />
          3X Leveraged ETFs
        </Button>
      </div>

      {/* Guardrail Overview Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-gradient-to-br from-pink-500/5 to-transparent border-pink-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Risk Guardrail Threshold</CardTitle>
            <Shield className="w-4 h-4 text-pink-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${thresholdUsd.toFixed(2)} USD</div>
            <p className="text-xs text-muted-foreground mt-1">
              Trades &lt; ${thresholdUsd} auto-execute. Trades &ge; ${thresholdUsd} require approval.
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-amber-500/5 to-transparent border-amber-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Pending Approvals</CardTitle>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-500">{pendingApprovals.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Awaiting Telegram or Web approval button clicks
            </p>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-emerald-500/5 to-transparent border-emerald-500/20">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Scanned US Tickers</CardTitle>
            <Zap className="w-4 h-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{signals.length} Tickers</div>
            <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
              {signals.map(s => s.symbol).join(', ')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Pending Approvals Section */}
      {pendingApprovals.length > 0 && (
        <Card className="border-amber-500/40 bg-amber-500/5">
          <CardHeader>
            <div className="flex items-center gap-2 text-amber-500">
              <AlertTriangle className="w-5 h-5" />
              <CardTitle>Trade Approvals Required (&ge; ${thresholdUsd} USD)</CardTitle>
            </div>
            <CardDescription>
              Review the AI reasonings below and confirm execution:
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {pendingApprovals.map((trade) => (
              <div
                key={trade.trade_id}
                className="flex flex-col md:flex-row items-start md:items-center justify-between p-4 rounded-xl border border-amber-500/20 bg-background/80 gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={trade.action === 'BUY' ? 'default' : 'destructive'} className="font-bold">
                      {trade.position_type || (trade.action === 'BUY' ? 'LONG' : 'SHORT')} {trade.action}
                    </Badge>
                    <span className="font-bold text-lg">{trade.symbol}</span>
                    <span className="text-sm text-muted-foreground">
                      {trade.quantity} shares @ ${trade.price.toFixed(2)}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    💡 AI Reason: <span className="italic text-foreground">{trade.reason}</span>
                  </p>
                  <p className="text-xs font-semibold text-pink-500">
                    Total Value: ${trade.total_usd.toFixed(2)} USD
                  </p>
                </div>

                <div className="flex items-center gap-2 w-full md:w-auto">
                  <Button
                    className="bg-emerald-600 hover:bg-emerald-700 text-white flex-1 md:flex-none"
                    disabled={isProcessing === trade.trade_id}
                    onClick={() => handleApproval(trade.trade_id, 'approve')}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Approve Trade
                  </Button>
                  <Button
                    variant="destructive"
                    className="flex-1 md:flex-none"
                    disabled={isProcessing === trade.trade_id}
                    onClick={() => handleApproval(trade.trade_id, 'reject')}
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Reject
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* AI & Lumibot Market Signals Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-pink-500" />
            Top Daily Performers, Cheap ETFs & Lumibot Analysis
          </CardTitle>
          <CardDescription>
            Ranked by daily gain %, technical momentum, and Lumibot historical backtest validation
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {signals.map((sig) => (
              <div
                key={sig.symbol}
                className="p-4 rounded-xl border bg-card hover:border-pink-500/30 transition-all space-y-3 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-xl tracking-tight">{sig.symbol}</span>
                        <Badge variant="outline" className="text-[10px]">
                          {sig.exchange}
                        </Badge>
                        {sig.badge_type && (
                          <Badge className="text-[10px] bg-pink-500/10 text-pink-400 border-pink-500/20">
                            {sig.badge_type}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-1">{sig.name}</p>
                    </div>

                    <div className="text-right">
                      <div className="font-bold text-lg">${sig.price.toFixed(2)}</div>
                      {sig.change_percent !== undefined && (
                        <div className="text-xs font-semibold text-emerald-400">
                          +{sig.change_percent}% Today
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t">
                    <span className="text-xs text-muted-foreground font-semibold">Signal Direction:</span>
                    <Badge
                      className={
                        sig.position_type === 'LONG' || sig.action === 'BUY'
                          ? 'bg-emerald-600 hover:bg-emerald-700 text-white font-bold gap-1'
                          : 'bg-red-600 hover:bg-red-700 text-white font-bold gap-1'
                      }
                    >
                      {sig.position_type === 'LONG' || sig.action === 'BUY' ? (
                        <ArrowUpRight className="w-3.5 h-3.5" />
                      ) : (
                        <ArrowDownRight className="w-3.5 h-3.5" />
                      )}
                      {sig.position_type || (sig.action === 'BUY' ? 'LONG' : 'SHORT')} {sig.action} ({sig.quantity} Qty)
                    </Badge>
                  </div>

                  {sig.lumibot && (
                    <div className="p-2.5 rounded-lg bg-pink-500/5 border border-pink-500/10 space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-pink-400 flex items-center gap-1">
                          <Activity className="w-3.5 h-3.5" />
                          Lumibot Backtest:
                        </span>
                        <Badge variant="outline" className="text-[10px] text-pink-300 border-pink-500/30 font-bold">
                          Win Rate: {sig.lumibot.win_rate}%
                        </Badge>
                      </div>
                      <div className="flex justify-between text-muted-foreground text-[11px] font-medium">
                        <span>Sharpe: <strong>{sig.lumibot.sharpe_ratio}</strong></span>
                        <span>Max DD: <strong>{sig.lumibot.max_drawdown}%</strong></span>
                        <span>PF: <strong>{sig.lumibot.profit_factor}</strong></span>
                      </div>
                    </div>
                  )}

                  {sig.target_price && sig.stop_loss && (
                    <div className="flex justify-between text-xs text-muted-foreground pt-1">
                      <span>Target: <strong className="text-emerald-400">${sig.target_price}</strong></span>
                      <span>Stop: <strong className="text-red-400">${sig.stop_loss}</strong></span>
                    </div>
                  )}

                  <p className="text-xs text-muted-foreground line-clamp-3 italic pt-1">
                    "{sig.reason}"
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Execution History Card */}
      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="w-5 h-5 text-blue-500" />
              AI Trade Execution History
            </CardTitle>
            <CardDescription>
              Recent automated and approved trades processed by the AI bot
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {history.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-lg border text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant={item.action === 'BUY' ? 'default' : 'destructive'}>
                      {item.position_type || (item.action === 'BUY' ? 'LONG' : 'SHORT')} {item.action}
                    </Badge>
                    <span className="font-bold">{item.symbol}</span>
                    <span className="text-muted-foreground">({item.quantity} @ ${item.price.toFixed(2)})</span>
                  </div>
                  <Badge variant={item.status === 'EXECUTED' ? 'outline' : 'secondary'}>
                    {item.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

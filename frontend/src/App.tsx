import { useEffect, useMemo, useState, useRef } from 'react'
import { JobForm } from './components/JobForm'
import { SuccessPage } from './components/SuccessPage'
import { ProgressBar } from './components/ProgressBar'
import { Textarea } from './components/ui/textarea'
import { Button } from './components/ui/button'
import logo from '../logo.png'
import { startAutoJob, startCopyJob, startInteractiveJob, getJob, getJobLogs } from './api'

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('idle')
  const [logs, setLogs] = useState<string[]>([])
  const [resultUrl, setResultUrl] = useState<string | null>(null)
  const [resultName, setResultName] = useState<string | null>(null)
  const [polling, setPolling] = useState<number>(0)
  const [projectDescription, setProjectDescription] = useState('')
  const getFormValuesRef = useRef<(() => any) | null>(null)
  const [copied, setCopied] = useState(false)
  const [showToast, setShowToast] = useState(false)

  const promptTemplate = `Prompt template : (Required)
Click the copy button to copy the prompt template to the clipboard. `

  const handleCopyTemplate = async () => {
    console.log('Copy button clicked, template length:', promptTemplate.length)
    
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        console.log('Using modern clipboard API')
        await navigator.clipboard.writeText(promptTemplate)
        console.log('Successfully copied to clipboard')
        setCopied(true)
        setShowToast(true)
        setTimeout(() => {
          setCopied(false)
          setShowToast(false)
        }, 2000)
      } else {
        console.log('Clipboard API not available, using fallback')
        throw new Error('Clipboard API not available')
      }
    } catch (err) {
      console.error('Clipboard API failed, trying fallback:', err)
      // Fallback method for browsers that don't support clipboard API
      const textArea = document.createElement('textarea')
      textArea.value = promptTemplate
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      textArea.style.opacity = '0'
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      
      try {
        const successful = document.execCommand('copy')
        if (successful) {
          console.log('Fallback copy successful')
          setCopied(true)
          setShowToast(true)
          setTimeout(() => {
            setCopied(false)
            setShowToast(false)
          }, 2000)
        } else {
          console.error('Fallback copy command returned false')
          alert('Failed to copy. Please copy manually from the textarea.')
        }
      } catch (fallbackErr) {
        console.error('Fallback copy error:', fallbackErr)
        alert('Failed to copy. Please copy manually from the textarea.')
      } finally {
        document.body.removeChild(textArea)
      }
    }
  }

  useEffect(() => {
    if (!jobId) return
    const interval = setInterval(async () => {
      try {
        const [j, l] = await Promise.all([getJob(jobId), getJobLogs(jobId)])
        setStatus(j.status)
        setLogs(l)
        if (j.status === 'succeeded') {
          setResultUrl(j?.result?.presentation_url || null)
          clearInterval(interval)
        }
        if (j.status === 'failed') {
          clearInterval(interval)
        }
      } catch (e) {
        // stop on error
        clearInterval(interval)
      }
    }, 1500)
    setPolling((p) => p + 1)
    return () => clearInterval(interval)
  }, [jobId])

  const busy = jobId !== null && (status === 'queued' || status === 'running')
  const statusLabel = useMemo(() => {
    switch (status) {
      case 'queued':
        return 'Queued'
      case 'running':
        return 'Generating'
      case 'succeeded':
        return 'Ready'
      case 'failed':
        return 'Failed'
      default:
        return 'Idle'
    }
  }, [status])

  const statusTone = useMemo(() => {
    switch (status) {
      case 'succeeded':
        return 'bg-emerald-400/20 text-emerald-300 border-emerald-400/30'
      case 'failed':
        return 'bg-rose-400/10 text-rose-300 border-rose-400/40'
      case 'running':
        return 'bg-cyan-400/20 text-cyan-200 border-cyan-400/30'
      case 'queued':
        return 'bg-amber-400/10 text-amber-200 border-amber-400/30'
      default:
        return 'bg-white/5 text-white/60 border-white/10'
    }
  }, [status])

  return (
    <div className="min-h-screen">
      {/* Toast Notification */}
      {showToast && (
        <div 
          className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 transition-all duration-300 ease-in-out"
          style={{
            animation: 'slideDown 0.3s ease-out'
          }}
        >
          <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl px-4 py-3 shadow-lg shadow-black/50">
            <p className="text-sm font-medium text-white">Prompt template Copied</p>
          </div>
        </div>
      )}
      
      <style>{`
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translate(-50%, -20px);
          }
          to {
            opacity: 1;
            transform: translate(-50%, 0);
          }
        }
      `}</style>
      
      <div className="mx-auto max-w-6xl px-5 py-10 sm:py-12 space-y-10">
        <header className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/10 shadow-inner shadow-black/30">
              <img src={logo} alt="PPT" className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-white">PPT Automation</h1>
              <p className="text-sm text-white/50">Craft clean, on-brand decks from your project brief in minutes.</p>
            </div>
          </div>
          <div className={`inline-flex items-center gap-2 rounded-full border px-4 py-1 text-sm font-medium ${statusTone}`}>
            <span className="h-2 w-2 rounded-full bg-current opacity-80" />
            {statusLabel}
          </div>
        </header>

        <section className="card space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-medium text-white">Generation status</p>
            <p className="text-sm text-white/60">
              {busy ? 'Hang tight—your presentation is being assembled.' : 'Provide your project details and generate a tailored deck instantly.'}
            </p>
          </div>

          <ProgressBar status={status as 'queued' | 'running' | 'succeeded' | 'failed' | 'idle'} logs={logs} />
        </section>

        {status === 'succeeded' && resultUrl ? (
          <SuccessPage
            presentationUrl={resultUrl}
            presentationName={resultName || undefined}
            onClose={() => {
              setResultUrl(null)
              setJobId(null)
              setStatus('idle')
            }}
          />
        ) : (
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
            <JobForm
              className="h-full"
              busy={busy}
              projectDescription={projectDescription}
              onFormValuesReady={(getFormValues) => {
                getFormValuesRef.current = getFormValues
              }}
              onStartAuto={async (payload) => {
                setJobId(null)
                setStatus('queued')
                setLogs([])
                setResultUrl(null)
                setResultName(payload?.output_title || 'Presentation')
                const { job_id } = await startAutoJob({ ...payload, project_description: projectDescription || undefined })
                setJobId(job_id)
              }}
              onStartCopy={async (payload) => {
                setJobId(null)
                setStatus('queued')
                setLogs([])
                setResultUrl(null)
                setResultName(payload?.new_title || 'Presentation')
                const { job_id } = await startCopyJob(payload)
                setJobId(job_id)
              }}
              onStartInteractive={async (payload) => {
                setJobId(null)
                setStatus('queued')
                setLogs([])
                setResultUrl(null)
                setResultName(payload?.output_title || 'Presentation')
                const { job_id } = await startInteractiveJob({ ...payload, project_description: projectDescription || undefined })
                setJobId(job_id)
              }}
            />

            <aside className="space-y-5">
              <div className="card space-y-3">
                <div>
                  <p className="text-sm font-medium text-white">Prompt for the presentation</p>
                  <p className="text-xs uppercase tracking-wide text-white/40">Give us the prompt for the presentation</p>
                </div>
                <Textarea
                  rows={10}
                  placeholder={promptTemplate}
                  value={projectDescription}
                  onChange={(e) => setProjectDescription(e.target.value)}
                />
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-white/40">You can tweak any details later directly inside Google Slides.</p>
                <Button
                  disabled={busy}
                  onClick={() => {
                    if (!getFormValuesRef.current) return
                    
                    const formValues = getFormValuesRef.current()
                    const { templateKey, customTemplate, company, project, proposalType, companyWebsite, sheetsId, sheetsRange, primaryColor, secondaryColor, accentColor, templates } = formValues
                    
                    // Generate dynamic output title from company name and project name
                    const dynamicOutputTitle = company && project ? `${company} - ${project}` : (company || project || 'Presentation')
                    
                    // Ensure colors are always sent (use defaults if empty)
                    const finalPrimaryColor = primaryColor || '#2563eb'
                    const finalSecondaryColor = secondaryColor || '#1e40af'
                    const finalAccentColor = accentColor || '#3b82f6'
                    
                    console.log('🎨 Sending colors to backend:', {
                      primary: finalPrimaryColor,
                      secondary: finalSecondaryColor,
                      accent: finalAccentColor
                    })
                    
                    const payload = {
                      template_id: (templateKey === 'custom' ? customTemplate : templates[templateKey].url) || undefined,
                      output_title: dynamicOutputTitle,
                      context: company || 'General Presentation',
                      profile: 'company',
                      project_name: project || undefined,
                      project_description: projectDescription || undefined,
                      company_name: company || undefined,
                      proposal_type: proposalType || undefined,
                      company_website: companyWebsite || undefined,
                      sheets_id: sheetsId || undefined,
                      sheets_range: sheetsRange || undefined,
                      auto_detect: false,
                      primary_color: finalPrimaryColor,
                      secondary_color: finalSecondaryColor,
                      accent_color: finalAccentColor,
                    }
                    
                    setJobId(null)
                    setStatus('queued')
                    setLogs([])
                    setResultUrl(null)
                    setResultName(dynamicOutputTitle)
                    startAutoJob({ ...payload, project_description: projectDescription || undefined }).then(({ job_id }) => {
                      setJobId(job_id)
                    })
                  }}
                >
                  {busy ? 'Working…' : 'Generate presentation'}
                </Button>
              </div>

              {resultUrl && status !== 'succeeded' && (
                <div className="card">
                  <p className="text-sm font-medium text-white">Latest presentation</p>
                  <a href={resultUrl} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center text-sm text-white hover:text-white/70">
                    {resultName || resultUrl}
                  </a>
                </div>
              )}
            </aside>
          </div>
        )}
      </div>
    </div>
  )
}



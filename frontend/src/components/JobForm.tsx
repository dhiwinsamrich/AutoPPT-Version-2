import { useMemo, useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { Input } from './ui/input'
import { Select } from './ui/select'
import { Button } from './ui/button'

type Props = {
  onStartAuto: (payload: any) => void
  onStartCopy: (payload: any) => void
  onStartInteractive: (payload: any) => void
  busy?: boolean
  className?: string
  projectDescription: string
  onFormValuesReady?: (getFormValues: () => any) => void
}

export function JobForm({ onStartAuto, onStartCopy, onStartInteractive, busy, className, projectDescription, onFormValuesReady }: Props) {
  // Preset templates dropdown
  const templates = useMemo(() => ({
    deck: {
      label: 'bdcode_',
      url: 'https://docs.google.com/presentation/d/1k7g7x8qjB4jImEXecYhY7mOLP5L4e4PH4zr5-btK4Q4/edit?slide=id.g3985ac1ea0e_0_260#slide=id.g3985ac1ea0e_0_260',
    },
    // custom: {
    //   label: 'Custom URL or ID',
    //   url: '',
    // },
  }), [])

  const [templateKey, setTemplateKey] = useState<keyof typeof templates>('deck')
  const [customTemplate, setCustomTemplate] = useState('')
  const [company, setCompany] = useState('BMW')
  const [project, setProject] = useState('Website Redesign')
  const [proposalType, setProposalType] = useState('Project Proposal')
  const [companyWebsite, setCompanyWebsite] = useState('https://www.bmw.com')
  const [sheetsId, setSheetsId] = useState('https://docs.google.com/spreadsheets/d/1yZJFKb-ZZ3hF1AE4JNJvg2MyCtYusfb6P3QBsBDaAmc/edit?usp=drive_web&ouid=107192840669358619002')
  const [sheetsRange, setSheetsRange] = useState('Sheet1')
  const [primaryColor, setPrimaryColor] = useState('#000000')
  const [secondaryColor, setSecondaryColor] = useState('#5BB4E5')
  const [accentColor, setAccentColor] = useState('#ffffff')
  const [copied, setCopied] = useState(false)

  const promptTemplate = `Project Title: (Title of the project)

Project Overview: (Overview of the project)

Features: (Maximum 15 features)

Feature 1: (Name of the feature)

Feature 2: (Name of the feature)

Feature 3: (Name of the feature)

Feature 4: (Name of the feature)

Feature 5: (Name of the feature)

Follow Reference Links: (Maximum 6 links)

https://example1.com
https://example2.com
https://example3.com
https://example4.com
https://example5.com
https://example6.com`

  const [showToast, setShowToast] = useState(false)

  const handleCopyTemplate = async () => {
    try {
      // Try modern clipboard API first
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(promptTemplate)
        setCopied(true)
        setShowToast(true)
        setTimeout(() => {
          setCopied(false)
          setShowToast(false)
        }, 2000)
      } else {
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
          setCopied(true)
          setShowToast(true)
          setTimeout(() => {
            setCopied(false)
            setShowToast(false)
          }, 2000)
        } else {
          alert('Failed to copy. Please copy manually.')
        }
      } catch (fallbackErr) {
        console.error('Fallback copy error:', fallbackErr)
        alert('Failed to copy. Please copy manually.')
      } finally {
        document.body.removeChild(textArea)
      }
    }
  }

  // Helper function to validate and format color input
  const handleColorTextInput = (value: string, setColor: (color: string) => void) => {
    // Allow user to type freely
    let formatted = value.trim()
    
    // Auto-add # if user starts typing without it
    if (formatted.length > 0 && !formatted.startsWith('#')) {
      formatted = '#' + formatted
    }
    
    // Only allow valid hex characters
    const hexPattern = /^#[0-9A-Fa-f]{0,6}$/
    if (formatted === '' || hexPattern.test(formatted)) {
      setColor(formatted)
    }
  }

  // Expose form values to parent component
  useEffect(() => {
    if (onFormValuesReady) {
      onFormValuesReady(() => ({
        templateKey,
        customTemplate,
        company,
        project,
        proposalType,
        companyWebsite,
        sheetsId,
        sheetsRange,
        primaryColor,
        secondaryColor,
        accentColor,
        templates,
      }))
    }
  }, [templateKey, customTemplate, company, project, proposalType, companyWebsite, sheetsId, sheetsRange, primaryColor, secondaryColor, accentColor, templates, onFormValuesReady])

  return (
    <>
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

      <div className={clsx('card space-y-8', className)}>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="md:col-span-1">
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">
            Template <span className="text-red-400">*</span>
          </label>
          <Select
            className="mt-2"
            value={templateKey}
            onChange={(e) => setTemplateKey(e.target.value as keyof typeof templates)}
            options={Object.entries(templates).map(([key, t]) => ({ label: t.label, value: key }))}
          />
        </div>
        {/* {templateKey === 'custom' && (
          <div className="md:col-span-1">
            <label className="text-xs font-medium uppercase tracking-wide text-white/50">Template ID or URL</label>
            <Input className="mt-2" placeholder="Slides URL or File ID" value={customTemplate} onChange={e => setCustomTemplate(e.target.value)} />
          </div>
        )} */}
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">
            Client / Organization Name <span className="text-red-400">*</span>
          </label>
          <Input className="mt-2" placeholder="Client / Organization Name (e.g. BMW, Woodland, etc.)" value={company} onChange={e => setCompany(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">
            Presentation Title <span className="text-red-400">*</span>
          </label>
          <Input className="mt-2" placeholder="Presentation Title (e.g. Website Redesign, Website Development, etc.)" value={project} onChange={e => setProject(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">
            Proposal Type <span className="text-red-400">*</span>
          </label>
          <Input className="mt-2" placeholder="Proposal Type (e.g. Project Proposal, Development Proposal, etc.)" value={proposalType} onChange={e => setProposalType(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">Company Website</label>
          <Input className="mt-2" placeholder="https://example.com" value={companyWebsite} onChange={e => setCompanyWebsite(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">
            Effort Estimation Sheet Link <span className="text-red-400">*</span>
          </label>
          <Input
            className="mt-2"
            placeholder="https://docs.google.com/spreadsheets/d/... or Sheet ID"
            value={sheetsId}
            onChange={e => setSheetsId(e.target.value)}
          />
        </div>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/5 px-4 py-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-white/50">Theme palette</p>
          <p className="text-sm text-white/70">Choose the brand colors you want on every slide.</p>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white/70">
          🎨
          <span>Syncs with prompt template</span>
        </span>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">Primary Color</label>
          <div className="mt-2 relative">
            <Input
              type="text"
              className="w-full font-mono pr-14"
              placeholder="#2563eb"
              value={primaryColor}
              onChange={e => handleColorTextInput(e.target.value, setPrimaryColor)}
              maxLength={7}
            />
            <div 
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-8 rounded border border-white/30 shadow-sm cursor-pointer"
              style={{ backgroundColor: primaryColor }}
              title={primaryColor}
              onClick={() => document.getElementById('primaryColorPicker')?.click()}
            />
            <input
              id="primaryColorPicker"
              type="color"
              className="hidden"
              value={primaryColor}
              onChange={e => setPrimaryColor(e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">Secondary Color</label>
          <div className="mt-2 relative">
            <Input
              type="text"
              className="w-full font-mono pr-14"
              placeholder="#1e40af"
              value={secondaryColor}
              onChange={e => handleColorTextInput(e.target.value, setSecondaryColor)}
              maxLength={7}
            />
            <div 
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-8 rounded border border-white/30 shadow-sm cursor-pointer"
              style={{ backgroundColor: secondaryColor }}
              title={secondaryColor}
              onClick={() => document.getElementById('secondaryColorPicker')?.click()}
            />
            <input
              id="secondaryColorPicker"
              type="color"
              className="hidden"
              value={secondaryColor}
              onChange={e => setSecondaryColor(e.target.value)}
            />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium uppercase tracking-wide text-white/50">Accent Color</label>
          <div className="mt-2 relative">
            <Input
              type="text"
              className="w-full font-mono pr-14"
              placeholder="#3b82f6"
              value={accentColor}
              onChange={e => handleColorTextInput(e.target.value, setAccentColor)}
              maxLength={7}
            />
            <div 
              className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-8 rounded border border-white/30 shadow-sm cursor-pointer"
              style={{ backgroundColor: accentColor }}
              title={accentColor}
              onClick={() => document.getElementById('accentColorPicker')?.click()}
            />
            <input
              id="accentColorPicker"
              type="color"
              className="hidden"
              value={accentColor}
              onChange={e => setAccentColor(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Copy Template Button - Below theme colors */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 text-red-500 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p className="text-xs text-white/60">
            Note: Prompt needs to be in the format of the prompt template to produce the best results.
          </p>
        </div>
      </div>
    </div>
    </>
  )
}



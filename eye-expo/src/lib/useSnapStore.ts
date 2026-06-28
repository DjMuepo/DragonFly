import { create } from 'zustand';

export type LicenseStatus = 'OK' | 'RESTRICTED' | 'UNKNOWN';
export type Novelty = 'COMMON' | 'SOMEWHAT_UNIQUE' | 'UNIQUE';
export type CaptureMode = 'single' | 'multi';

export type MatchCandidate = {
  hosted?: boolean;
  externalUrl?: string;
  id: string;
  title: string;
  similarity: number;
  license: LicenseStatus;
  previewUrl?: string;
};

export type ScanImage = {
  uri: string;
  label?: string;
  confidence?: number;
};

export type UserProfile = {
  name?: string;
  interests: string[];
  skillLevel?: 'beginner' | 'intermediate' | 'advanced';
};

type JobStatus = 'created' | 'uploaded' | 'processing' | 'done' | 'error';

type SnapState = {
  // New one-photo MVP flow
  heroUri?: string;
  cutoutUri?: string;
  targetLabel?: string;
  captured: ScanImage[];
  generatedModelUrl?: string;
  generatedModelName?: string;

  setHeroUri: (uri?: string) => void;
  setCutoutUri: (uri?: string) => void;
  setTargetLabel: (label?: string) => void;
  addCaptured: (image: ScanImage) => void;
  setGeneratedModel: (url?: string, name?: string) => void;
  clear: () => void;

  // Compatibility with the larger existing app
  captureMode: CaptureMode;
  burstUris: string[];
  jobId?: string;
  jobStatus?: JobStatus;
  previewUrl?: string;
  modelDownloadUrl?: string;
  maskUri?: string;
  tapPoint?: { x: number; y: number };
  matches: MatchCandidate[];
  novelty?: Novelty;
  selectedMatchId?: string;
  sessionId: string;
  structuralParams: any;
  structuralReport?: any;
  lastStrengthen?: { before: any; after: any; delta: number };
  visionClassify?: any;
  visionDraft?: any;
  visionSegment?: any;
  visionPreviewUrl?: string;
  visionReconstruct?: any;
  userProfile: UserProfile;
  authToken?: string;
  currentUser?: any;
  correctedFamily?: string;
  selectedPrinter?: any;
  printRequest?: any;
  sharedDesign?: any;

  setCaptureMode: (mode: CaptureMode) => void;
  setCapture: (heroUri?: string, burstUris?: string[]) => void;
  setJob: (jobId?: string) => void;
  setJobStatus: (status?: JobStatus) => void;
  setJobResultLinks: (previewUrl?: string, modelDownloadUrl?: string) => void;
  setTapPoint: (x: number, y: number) => void;
  setMask: (maskUri?: string) => void;
  setMatches: (matches: MatchCandidate[], novelty: Novelty) => void;
  selectMatch: (id?: string) => void;
  setStructuralParams: (p: any) => void;
  setStructuralReport: (r: any) => void;
  setLastStrengthen: (ls?: { before: any; after: any; delta: number }) => void;
  setVisionClassify: (v: any) => void;
  setVisionDraft: (v: any) => void;
  setVisionSegment: (v: any) => void;
  setVisionPreviewUrl: (v?: string) => void;
  setVisionReconstruct: (v: any) => void;
  setUserProfile: (profile: Partial<UserProfile>) => void;
  setAuth: (token?: string, user?: any) => void;
  setCorrectedFamily: (family?: string) => void;
  setSelectedPrinter: (printer?: any) => void;
  setPrintRequest: (req?: any) => void;
  setSharedDesign: (d?: any) => void;
  reset: () => void;
};

const newSessionId = () => `${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`;
const initialStructural = {
  thickness: 1.0,
  has_rib: false,
  has_fillet: false,
  hole_count: 0,
  overhang_risk: 0.0,
  cantilever: 0.0,
  aspect_ratio: 1.0,
  joint_type: 'unknown',
};

const resetState = () => ({
  heroUri: undefined,
  cutoutUri: undefined,
  targetLabel: undefined,
  captured: [],
  generatedModelUrl: undefined,
  generatedModelName: undefined,
  captureMode: 'single' as CaptureMode,
  burstUris: [],
  jobId: undefined,
  jobStatus: undefined,
  previewUrl: undefined,
  modelDownloadUrl: undefined,
  maskUri: undefined,
  tapPoint: undefined,
  matches: [],
  novelty: undefined,
  selectedMatchId: undefined,
  sessionId: newSessionId(),
  structuralParams: initialStructural,
  structuralReport: undefined,
  lastStrengthen: undefined,
  visionClassify: undefined,
  visionDraft: undefined,
  visionSegment: undefined,
  visionPreviewUrl: undefined,
  visionReconstruct: undefined,
  correctedFamily: undefined,
  selectedPrinter: undefined,
  printRequest: undefined,
  sharedDesign: undefined,
});

export const useSnapStore = create<SnapState>((set, get) => ({
  ...resetState(),
  userProfile: { interests: [], skillLevel: 'beginner' },
  authToken: undefined,
  currentUser: undefined,

  setHeroUri: (heroUri) => set({ heroUri }),
  setCutoutUri: (cutoutUri) => set({ cutoutUri }),
  setTargetLabel: (targetLabel) => set({ targetLabel }),
  addCaptured: (image) => set((state) => ({ captured: [...state.captured, image] })),
  setGeneratedModel: (generatedModelUrl, generatedModelName) => set({ generatedModelUrl, generatedModelName }),
  clear: () => set(resetState()),

  setCaptureMode: (captureMode) => set({ captureMode }),
  setCapture: (heroUri, burstUris = []) => set({ heroUri, burstUris }),
  setJob: (jobId) => set({ jobId }),
  setJobStatus: (jobStatus) => set({ jobStatus }),
  setJobResultLinks: (previewUrl, modelDownloadUrl) => set({ previewUrl, modelDownloadUrl }),
  setTapPoint: (x, y) => set({ tapPoint: { x, y } }),
  setMask: (maskUri) => set({ maskUri }),
  setMatches: (matches, novelty) => set({ matches, novelty }),
  selectMatch: (selectedMatchId) => set({ selectedMatchId }),
  setStructuralParams: (p) => set({ structuralParams: { ...get().structuralParams, ...p } }),
  setStructuralReport: (structuralReport) => set({ structuralReport }),
  setLastStrengthen: (lastStrengthen) => set({ lastStrengthen }),
  setVisionClassify: (visionClassify) => set({ visionClassify }),
  setVisionDraft: (visionDraft) => set({ visionDraft }),
  setVisionSegment: (visionSegment) => set({ visionSegment }),
  setVisionPreviewUrl: (visionPreviewUrl) => set({ visionPreviewUrl }),
  setVisionReconstruct: (visionReconstruct) => set({ visionReconstruct }),
  setUserProfile: (profile) =>
    set({ userProfile: { ...get().userProfile, ...profile, interests: profile.interests ?? get().userProfile.interests } }),
  setAuth: (authToken, currentUser) => set({ authToken, currentUser }),
  setCorrectedFamily: (correctedFamily) => set({ correctedFamily }),
  setSelectedPrinter: (selectedPrinter) => set({ selectedPrinter }),
  setPrintRequest: (printRequest) => set({ printRequest }),
  setSharedDesign: (sharedDesign) => set({ sharedDesign }),
  reset: () => set(resetState()),
}));

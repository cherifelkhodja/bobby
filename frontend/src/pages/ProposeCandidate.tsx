import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { CheckCircle, FileText } from 'lucide-react';

import { getPublishedOpportunity } from '../api/publishedOpportunities';
import { cooptationsApi } from '../api/cooptations';
import { getErrorMessage } from '../api/client';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { PageSpinner } from '../components/ui/Spinner';

const cooptationSchema = z.object({
  candidate_first_name: z.string().min(1, 'Prenom requis'),
  candidate_last_name: z.string().min(1, 'Nom requis'),
  candidate_email: z.string().email('Email invalide'),
  candidate_civility: z.enum(['M', 'Mme']),
  candidate_phone: z.string().min(1, 'Telephone requis'),
  candidate_daily_rate: z.coerce.number().positive('TJM requis'),
  candidate_note: z.string().max(2000).optional(),
});

type CooptationFormData = z.infer<typeof cooptationSchema>;

const ALLOWED_EXTENSIONS = ['.pdf', '.docx'];
const ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export default function ProposeCandidate() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(true);
  const [cvFile, setCvFile] = useState<File | null>(null);
  const [cvError, setCvError] = useState<string | null>(null);

  // Fetch opportunity
  const {
    data: opportunity,
    isLoading: loadingOpportunity,
    error: opportunityError,
  } = useQuery({
    queryKey: ['published-opportunity', id],
    queryFn: () => getPublishedOpportunity(id!),
    enabled: !!id,
  });

  // Form
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CooptationFormData>({
    resolver: zodResolver(cooptationSchema),
    defaultValues: {
      candidate_civility: 'M',
    },
  });

  // Submit mutation
  const mutation = useMutation({
    mutationFn: cooptationsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-cooptations'] });
      queryClient.invalidateQueries({ queryKey: ['my-stats'] });
      toast.success('Cooptation soumise avec succes !');
      reset();
      setCvFile(null);
      setCvError(null);
      setShowForm(false);
    },
    onError: (error) => {
      toast.error(getErrorMessage(error));
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setCvError(null);
    if (!file) return;

    const hasValidExtension = ALLOWED_EXTENSIONS.some((ext) =>
      file.name.toLowerCase().endsWith(ext)
    );
    if (!ALLOWED_TYPES.includes(file.type) && !hasValidExtension) {
      setCvError('Format non supporte. Utilisez PDF ou DOCX.');
      return;
    }
    if (file.size > MAX_SIZE) {
      setCvError('Fichier trop volumineux. Maximum 10 Mo.');
      return;
    }
    setCvFile(file);
  };

  const removeFile = () => {
    setCvFile(null);
    setCvError(null);
  };

  const onSubmit = (data: CooptationFormData) => {
    if (!id) return;
    if (!cvFile) {
      setCvError('Le CV est obligatoire');
      return;
    }
    mutation.mutate({
      opportunity_id: id,
      ...data,
      cv: cvFile,
    });
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  if (loadingOpportunity) {
    return <PageSpinner />;
  }

  if (opportunityError || !opportunity) {
    return (
      <div className="text-center py-16">
        <h2 className="text-[15px] font-bold text-ink mb-2">Opportunite non trouvee</h2>
        <p className="notec mb-6">Cette opportunite n'existe pas ou a ete supprimee.</p>
        <Button onClick={() => navigate('/opportunities')}>Retour aux opportunites</Button>
      </div>
    );
  }

  const isActive = opportunity.status === 'published';

  return (
    <div className="max-w-[680px]">
      <Link
        to={`/opportunities/${id}`}
        className="bc block cursor-pointer !text-mut2 hover:!text-mut"
      >
        ← Retour à l'opportunité
      </Link>

      {/* Opportunity banner */}
      <div className="card !bg-srf2 mt-2">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="ml">Opportunité</p>
            <p className="dn !text-[14.5px] mt-[3px] truncate">{opportunity.title}</p>
            <p className="ds mt-1">
              Publiée le {formatDate(opportunity.created_at)}
              {opportunity.end_date && ` · fin prévue ${formatDate(opportunity.end_date)}`}
            </p>
          </div>
          <span className={`st shrink-0 ${isActive ? 'st-grn' : 'st-sla'}`}>
            <span className="dot" />
            {isActive ? 'Active' : opportunity.status_display}
          </span>
        </div>
      </div>

      {showForm ? (
        <div className="card mt-3.5">
          <h3 className="ct">Proposer un candidat</h3>
          <p className="cs mb-4">
            Remplissez les informations du profil que vous souhaitez recommander.
          </p>

          <form onSubmit={handleSubmit(onSubmit)}>
            {/* Identity */}
            <p className="ml mb-2.5">Identité</p>
            <div className="grid grid-cols-1 sm:grid-cols-[110px_1fr_1fr] gap-4">
              <div>
                <label className="f-lab" htmlFor="candidate_civility">
                  Civilité
                </label>
                <select
                  id="candidate_civility"
                  className="f-in !px-2.5"
                  {...register('candidate_civility')}
                >
                  <option value="M">M.</option>
                  <option value="Mme">Mme</option>
                </select>
              </div>
              <Input
                label="Prénom"
                error={errors.candidate_first_name?.message}
                {...register('candidate_first_name')}
              />
              <Input
                label="Nom"
                error={errors.candidate_last_name?.message}
                {...register('candidate_last_name')}
              />
            </div>

            {/* Contact */}
            <p className="ml mt-4 mb-2.5">Contact &amp; tarif</p>
            <div className="f-grid">
              <Input
                label="Email"
                type="email"
                error={errors.candidate_email?.message}
                {...register('candidate_email')}
              />
              <Input
                label="Téléphone"
                placeholder="0612345678"
                error={errors.candidate_phone?.message}
                {...register('candidate_phone')}
              />
            </div>
            <div className="mt-3.5 max-w-[220px]">
              <Input
                label="TJM souhaité (€ / jour)"
                type="number"
                placeholder="500"
                error={errors.candidate_daily_rate?.message}
                {...register('candidate_daily_rate')}
              />
            </div>

            {/* CV Upload */}
            <p className="ml mt-4 mb-2.5">CV *</p>
            {cvFile ? (
              <div className="filecard">
                <div className="dico">
                  <FileText className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="dn truncate">{cvFile.name}</p>
                  <p className="ds">{formatFileSize(cvFile.size)}</p>
                </div>
                <Button type="button" variant="secondary" size="sm" onClick={removeFile}>
                  Retirer
                </Button>
              </div>
            ) : (
              <label className="drop block !p-[22px]">
                <p className="dropt !mt-0">
                  <b className="text-prit">Cliquez pour choisir</b> ou glissez-déposez
                </p>
                <p className="drops">PDF ou DOCX · 10 Mo max</p>
                <input
                  type="file"
                  className="hidden"
                  accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  onChange={handleFileChange}
                />
              </label>
            )}
            {cvError && <p className="f-hint !text-redt">{cvError}</p>}

            {/* Note */}
            <p className="ml mt-4 mb-2.5">Commentaire</p>
            <textarea
              className="f-ta"
              placeholder="Informations complémentaires sur le candidat…"
              {...register('candidate_note')}
            />
            {errors.candidate_note && (
              <p className="f-hint !text-redt">{errors.candidate_note.message}</p>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 mt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={() => navigate(`/opportunities/${id}`)}
              >
                Annuler
              </Button>
              <Button type="submit" isLoading={mutation.isPending} disabled={!isActive}>
                Soumettre la cooptation
              </Button>
            </div>
          </form>
        </div>
      ) : (
        <div className="card mt-3.5 text-center px-[22px] py-9">
          <div className="okbox !inline-flex !m-0 !mb-3.5">
            <CheckCircle className="h-4 w-4" />
            <span>Cooptation soumise avec succès !</span>
          </div>
          <p className="notec">
            Votre recommandation a bien été enregistrée — suivez son avancement dans « Mes
            cooptations ».
          </p>
          <div className="flex justify-center gap-2 mt-4">
            <Button variant="secondary" onClick={() => setShowForm(true)}>
              Proposer un autre candidat
            </Button>
            <Button onClick={() => navigate('/my-cooptations')}>Voir mes cooptations</Button>
          </div>
        </div>
      )}
    </div>
  );
}

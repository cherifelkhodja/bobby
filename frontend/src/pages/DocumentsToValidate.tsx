import { useState } from 'react';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText } from 'lucide-react';
import { toast } from 'sonner';

import { vigilanceApi } from '../api/vigilance';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { PageSpinner } from '../components/ui/Spinner';
import { DocumentViewerModal } from '../components/vigilance/DocumentViewerModal';
import { formatDate } from '../components/vigilance/dateUtils';
import { getErrorMessage } from '../api/client';
import type { VigilanceDocument } from '../types';

interface QueueItem {
  doc: VigilanceDocument;
  thirdPartyName: string;
}

export default function DocumentsToValidate() {
  const queryClient = useQueryClient();
  const [viewingDoc, setViewingDoc] = useState<VigilanceDocument | null>(null);
  const [rejectTarget, setRejectTarget] = useState<VigilanceDocument | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  // Compteur serveur des documents au statut « reçu » (référence pour savoir
  // si la file est complète après le premier passage).
  const dashboardQuery = useQuery({
    queryKey: ['compliance-dashboard'],
    queryFn: () => vigilanceApi.getDashboard(),
  });

  // Liste des tiers en une seule requête, pour savoir où chercher les documents.
  const { data: thirdParties, isPending: tpsPending } = useQuery({
    queryKey: ['vigilance-third-parties', 'documents-queue'],
    queryFn: () => vigilanceApi.listThirdParties({ limit: 200 }),
  });

  const allTps = thirdParties?.items ?? [];
  // Les documents à vérifier vivent en priorité chez les tiers « en cours de
  // vérification » — on interroge ceux-là d'abord.
  const primaryTps = allTps.filter((tp) => tp.compliance_status === 'under_review');
  const secondaryTps = allTps.filter((tp) => tp.compliance_status !== 'under_review');

  const primaryQueries = useQueries({
    queries: primaryTps.map((tp) => ({
      queryKey: ['vigilance-documents', tp.id],
      queryFn: () => vigilanceApi.getThirdPartyDocuments(tp.id),
    })),
  });

  const primaryDone = primaryQueries.every((q) => !q.isPending);
  const primaryReceivedCount = primaryQueries.reduce(
    (acc, q) =>
      acc + (q.data?.documents.filter((d) => d.status === 'received').length ?? 0),
    0,
  );

  // Si le compteur global du dashboard indique des documents « reçus » ailleurs
  // (tiers non conformes, expirations proches…), on élargit la recherche.
  const expected = dashboardQuery.data?.documents_pending_review;
  const needSecondary =
    secondaryTps.length > 0 &&
    primaryDone &&
    !dashboardQuery.isPending &&
    (expected === undefined || primaryReceivedCount < expected);

  const secondaryQueries = useQueries({
    queries: secondaryTps.map((tp) => ({
      queryKey: ['vigilance-documents', tp.id],
      queryFn: () => vigilanceApi.getThirdPartyDocuments(tp.id),
      enabled: needSecondary,
    })),
  });

  const secondaryDone = !needSecondary || secondaryQueries.every((q) => !q.isPending);

  const queue: QueueItem[] = [];
  for (const q of [...primaryQueries, ...secondaryQueries]) {
    if (!q.data) continue;
    for (const doc of q.data.documents) {
      if (doc.status === 'received') {
        queue.push({ doc, thirdPartyName: q.data.company_name || 'Tiers inconnu' });
      }
    }
  }
  // Les plus anciens en premier (ordre de traitement de la file).
  queue.sort((a, b) => (a.doc.uploaded_at ?? '').localeCompare(b.doc.uploaded_at ?? ''));

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['vigilance-documents'] });
    queryClient.invalidateQueries({ queryKey: ['vigilance-third-parties'] });
    queryClient.invalidateQueries({ queryKey: ['compliance-dashboard'] });
    queryClient.invalidateQueries({ queryKey: ['compliance', 'nav-count'] });
  };

  const validateMutation = useMutation({
    mutationFn: (docId: string) => vigilanceApi.validateDocument(docId),
    onSuccess: () => {
      toast.success('Document validé.');
      setViewingDoc(null);
      invalidateAll();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ docId, reason }: { docId: string; reason: string }) =>
      vigilanceApi.rejectDocument(docId, reason),
    onSuccess: () => {
      toast.success('Document rejeté.');
      setRejectTarget(null);
      setRejectReason('');
      setViewingDoc(null);
      invalidateAll();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const closeRejectModal = () => {
    setRejectTarget(null);
    setRejectReason('');
  };

  const isLoading =
    tpsPending ||
    dashboardQuery.isPending ||
    !primaryDone ||
    (needSecondary && !secondaryDone);

  if (isLoading && queue.length === 0) return <PageSpinner />;

  return (
    <div>
      <p className="bc">Contrats / Documents à valider</p>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="h1">Documents à valider</h1>
          <p className="sub">
            Reçus via le portail tiers · contrôles automatiques déjà passés
          </p>
        </div>
        <span className="st st-blu">
          <span className="dot" />
          {queue.length} en file
        </span>
      </div>

      <div className="card mt-[18px] !pt-1 !pb-2 !px-5">
        {queue.map(({ doc, thirdPartyName }) => (
          <div key={doc.id} className="qrow">
            <div className="dico">
              <FileText className="h-4 w-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="dn truncate">{doc.document_type_display}</p>
              <p className="ds truncate">
                {thirdPartyName} · reçu le {formatDate(doc.uploaded_at)}
                {doc.file_name ? ` · ${doc.file_name}` : ''}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button variant="secondary" size="sm" onClick={() => setViewingDoc(doc)}>
                Aperçu
              </Button>
              <Button
                size="sm"
                onClick={() => validateMutation.mutate(doc.id)}
                disabled={validateMutation.isPending}
              >
                Valider
              </Button>
              <Button
                variant="secondary"
                size="sm"
                className="!text-redt"
                onClick={() => {
                  setRejectTarget(doc);
                  setRejectReason('');
                }}
              >
                Rejeter
              </Button>
            </div>
          </div>
        ))}

        {queue.length === 0 && (
          <div className="text-center py-9">
            <p className="dn">File vide — tout est vérifié</p>
            <p className="ds mt-1.5">
              Les prochains documents reçus via le portail apparaîtront ici.
            </p>
          </div>
        )}
      </div>

      {/* Aperçu du document */}
      {viewingDoc && (
        <DocumentViewerModal
          doc={viewingDoc}
          onClose={() => setViewingDoc(null)}
          onValidate={() => validateMutation.mutate(viewingDoc.id)}
          onRejectStart={() => {
            setRejectTarget(viewingDoc);
            setRejectReason('');
            setViewingDoc(null);
          }}
          isValidating={validateMutation.isPending}
        />
      )}

      {/* Rejet avec motif */}
      <Modal isOpen={!!rejectTarget} onClose={closeRejectModal} title="Rejeter le document">
        {rejectTarget && (
          <div className="space-y-4">
            <p className="notec">
              Le rejet de{' '}
              <span className="font-semibold text-ink">
                {rejectTarget.document_type_display}
              </span>{' '}
              sera notifié au tiers, qui pourra déposer un nouveau document via le portail.
            </p>
            <div>
              <label htmlFor="reject-reason" className="f-lab">
                Motif du rejet *
              </label>
              <textarea
                id="reject-reason"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Motif du rejet (min. 5 caractères)…"
                className="f-ta"
                rows={3}
                autoFocus
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="secondary"
                onClick={closeRejectModal}
                disabled={rejectMutation.isPending}
              >
                Annuler
              </Button>
              <Button
                variant="danger"
                onClick={() =>
                  rejectMutation.mutate({ docId: rejectTarget.id, reason: rejectReason })
                }
                disabled={rejectReason.trim().length < 5}
                isLoading={rejectMutation.isPending}
              >
                Rejeter le document
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

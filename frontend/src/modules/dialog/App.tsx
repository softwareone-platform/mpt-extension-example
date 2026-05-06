import { useMPTContext, useMPTModal } from '@mpt-extension/sdk-react';
import { Button } from '@softwareone-platform/sdk-react-ui-v0/button';

import '../../fixes/modal-layout.scss';

interface DialogContext {
  data: {
    subscriptionId: string;
    name: string;
  };
}

export default function App() {
  const { data } = useMPTContext<DialogContext>();
  const { close } = useMPTModal();

  if (!data) return null;

  return <div className="dialog">
    <div className="dialog__header">
      <div className="dialog__title">Confirm subscription terms</div>
    </div>
    <div className="dialog__content">
      <p>
        You are about to accept the terms and conditions
        for <strong>{data.name}</strong> ({data.subscriptionId}).
        Please review the terms carefully before proceeding.
      </p>
      <p>
        By accepting, you agree to the service terms, usage policies,
        and billing conditions associated with this subscription.
      </p>
    </div>
    <div className="dialog__actions">
      <Button type="secondary" onClick={() => close({ accepted: false })}>Decline</Button>
      <Button type="primary" onClick={() => close({ accepted: true })}>Accept</Button>
    </div>
  </div>;
}

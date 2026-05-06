import { useState } from 'react';

import { useMPTModal } from '@mpt-extension/sdk-react';
import { Button } from '@softwareone-platform/sdk-react-ui-v0/button';
import { Divider } from '@softwareone-platform/sdk-react-ui-v0/divider';

import { ShowCode } from './elements/ShowCode';

import './Modals.scss';

const codeOpen = `
import { useMPTModal } from '@mpt-extension/sdk-react';

function MyComponent() {
  const { open } = useMPTModal();

  // open(plugId, config?) launches a platform modal that renders
  // the Plug with the given ID.
  //
  // config.context — optional data passed to the modal Plug
  //   (accessible inside via useMPTContext())
  //
  // config.onClose — callback invoked when the modal is closed;
  //   receives whatever data the modal passed to close()

  open('my-dialog', {
    context: { subscriptionId: 'SUB-1234', name: 'My Subscription' },
    onClose: (result) => {
      // result is whatever the modal passed to close(data).
      // If the user dismissed the modal without an explicit action
      // (e.g. clicking outside), result is undefined — ignore it
      // so you don't overwrite a previous decision.
      if (result) {
        console.log(result); // e.g. { accepted: true }
      }
    },
  });
}
`;

const codeClose = `
// Inside the modal Plug — call close() to dismiss the modal
// and send data back to the opener.

import { useMPTModal } from '@mpt-extension/sdk-react';

function TermsDialog() {
  const { close } = useMPTModal();

  return (
    <>
      <button onClick={() => close({ accepted: true })}>Accept</button>
      <button onClick={() => close({ accepted: false })}>Decline</button>
    </>
  );
}

// The user can also close the modal by clicking outside it.
// In that case onClose fires with no data (undefined) — this is
// not the same as an explicit decline.
//
// Only the Plug that called open() receives the onClose callback.
// Other Plugs on the page are not notified about the modal lifecycle.
`;

interface TermsResult {
  accepted: boolean;
}

type TermsOutcome = 'accepted' | 'declined';

interface ProvisionResult {
  name: string;
  region: string;
  tier: string;
}

export function Modals() {
  const { open } = useMPTModal();
  const [termsOutcome, setTermsOutcome] = useState<TermsOutcome | null>(null);
  const [provisionResult, setProvisionResult] = useState<ProvisionResult | null>(null);

  const openTermsDialog = () => {
    open('dialog', {
      context: { subscriptionId: 'SUB-9999-9999', name: 'Production SaaS Suite' },
      onClose: (data?: TermsResult) => {
        if (data) setTermsOutcome(data.accepted ? 'accepted' : 'declined');
      },
    });
  };

  const openProvisionWizard = () => {
    open('wizard', {
      onClose: (data?: ProvisionResult) => {
        if (data) setProvisionResult(data);
      },
    });
  };

  return <>
    <h2>Modals</h2>
    <p>
      Use <code>useMPTModal()</code> to open platform modals that render a separate Plug.
      The hook returns two methods: <code>open(plugId, config?)</code> launches the
      modal, <code>close(data?)</code> dismisses it from inside. The opener can pass
      additional context to the modal via <code>config.context</code>, and the modal can
      send data back to the opener via <code>close(data)</code>. The
      {' '}<code>onClose</code> callback fires only in the Plug that called{' '}
      <code>open()</code> — other Plugs on the page are not notified.
    </p>

    <h3>Dialog: confirm subscription terms</h3>
    <p>
      Opens a dialog Plug, passing a subscription ID and name as context.
      The dialog returns whether the terms were accepted or declined.
    </p>
    <div className="modal-demo-row">
      <Button type="primary" onClick={openTermsDialog}>Open terms dialog</Button>
      {termsOutcome && (
        <span>
          Result: <code>{termsOutcome}</code>
        </span>
      )}
    </div>

    <Divider />

    <h3>Wizard: provision a new resource</h3>
    <p>
      Opens a multi-step wizard Plug with no extra context.
      On completion the wizard returns the assembled object.
    </p>
    <div className="modal-demo-row">
      <Button type="primary" onClick={openProvisionWizard}>Open provision wizard</Button>
      {provisionResult && (
        <span>
          Result: <code>{JSON.stringify(provisionResult)}</code>
        </span>
      )}
    </div>

    <Divider />

    <h3>Opening a modal</h3>
    <ShowCode>{codeOpen}</ShowCode>

    <h3>Closing from inside</h3>
    <ShowCode>{codeClose}</ShowCode>
  </>;
}

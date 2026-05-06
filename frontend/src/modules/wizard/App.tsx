import { useState } from 'react';

import { useMPTModal } from '@mpt-extension/sdk-react';

import './App.scss';
import { Input } from '@softwareone-platform/sdk-react-ui-v0/input';
import { Select, SelectItem } from '@softwareone-platform/sdk-react-ui-v0/select';
import { StepProps, Wizard } from '@softwareone-platform/sdk-react-ui-v0/wizard';

const regionOptions: SelectItem[] = [
  { label: 'EU West (Frankfurt)', value: 'eu-west' },
  { label: 'EU North (Stockholm)', value: 'eu-north' },
  { label: 'US East (Virginia)', value: 'us-east' },
  { label: 'AP Southeast (Singapore)', value: 'ap-southeast' },
];

const tierOptions: SelectItem[] = [
  { label: 'Starter', value: 'starter' },
  { label: 'Professional', value: 'professional' },
  { label: 'Enterprise', value: 'enterprise' },
];

const steps: StepProps[] = [
  { title: 'General', secondaryTitle: 'Name your resource' },
  { title: 'Configuration', secondaryTitle: 'Region and tier' },
  {
    title: 'Review',
    secondaryTitle: 'Confirm and provision',
    nextButton: { label: 'Provision' },
  },
];

export default function App() {
  const { close } = useMPTModal();

  const [name, setName] = useState('');
  const [region, setRegion] = useState('');
  const [tier, setTier] = useState('');

  return <div className="wizard-container">
    <Wizard
    stepsProps={steps}
    onClose={() => close()}
    onSave={() => close({ name, region, tier })}
    navigation={{ next: 'Continue', back: 'Back', close: 'Cancel', finish: 'Provision' }}
  >
    <Wizard.Header isToShowCloseButton>Provision a new resource</Wizard.Header>
    <Wizard.Content>
      <Wizard.Content.Steps />
      <Wizard.Content.StepContent>
        {({ activeStepIndex }) => <>
          {activeStepIndex === 0 && <div>
            <Input
              name="resourceName"
              label="Resource name"
              placeholder="e.g. production-db-01"
              value={name}
              onChange={(e) => setName((e.target as HTMLInputElement).value)}
              description="A human-readable name for this resource"
            />
          </div>}

          {activeStepIndex === 1 && <div className="wizard-step-fields">
            <Select
              options={regionOptions}
              value={region}
              onChange={setRegion}
              controlLabel="Region"
              placeholder="Select a region"
            />
            <Select
              options={tierOptions}
              value={tier}
              onChange={setTier}
              controlLabel="Tier"
              placeholder="Select a tier"
            />
          </div>}

          {activeStepIndex === 2 && <div>
            <p>Please review your resource configuration before provisioning:</p>
            <table>
              <tbody>
                <tr><td><strong>Name</strong></td><td>{name || '—'}</td></tr>
                <tr><td><strong>Region</strong></td><td>{regionOptions.find(o => o.value === region)?.label || '—'}</td></tr>
                <tr><td><strong>Tier</strong></td><td>{tierOptions.find(o => o.value === tier)?.label || '—'}</td></tr>
              </tbody>
            </table>
          </div>}
        </>}
      </Wizard.Content.StepContent>
    </Wizard.Content>
    <Wizard.Actions />
  </Wizard>
  </div>;
}

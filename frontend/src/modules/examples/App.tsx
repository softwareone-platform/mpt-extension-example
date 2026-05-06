import { Tab, Tabs } from '@softwareone-platform/sdk-react-ui-v0/tabs'
import { DesignSystemOptionsProvider } from '@softwareone-platform/sdk-react-ui-v0/utils';
import {Routes, Route, useParams, useNavigate} from "react-router";
import {useEffect} from "react";

import { Intro } from './views/Intro';
import { Basics } from './views/Basics';
import { Elements } from './views/Elements';
import { Context } from './views/Context';
import { Api } from './views/Api';
import { Modals } from './views/Modals';


const View = () => {
  const { tab } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    if (!tab) navigate('/intro');
  }, [tab]);

  if (!tab) return null;

  return <DesignSystemOptionsProvider
    value={{
      languageCode: 'en-GB',
      dateFormat: 'dd MMM yyy',
      timeFormat: 'HH:mm',
      inputDateFormat: 'P',
    }}
  >
    <Tabs selectedTabId={tab} onTabChange={(id) => navigate(`/${id}`)}>
      <Tab id="intro" title="Introduction">
        <Tab.Content>
          <Intro/>
        </Tab.Content>
      </Tab>
      <Tab id="basics" title="Basics">
        <Tab.Content>
          <Basics/>
        </Tab.Content>
      </Tab>
      <Tab id="elements" title="UI elements">
        <Tab.Content>
          <Elements />
        </Tab.Content>
      </Tab>
      <Tab id="context" title="Context">
        <Tab.Content>
          <Context/>
        </Tab.Content>
      </Tab>
      <Tab id="api" title="API calls">
        <Tab.Content>
          <Api/>
        </Tab.Content>
      </Tab>
      <Tab id="modals" title="Modals">
        <Tab.Content>
          <Modals />
        </Tab.Content>
      </Tab>
    </Tabs>
  </DesignSystemOptionsProvider>
}

export default function App() {
  return <>
    <Routes>
      <Route path="/:tab" element={<View />} />
      <Route path="/" element={<View />} />
    </Routes>
  </>
}
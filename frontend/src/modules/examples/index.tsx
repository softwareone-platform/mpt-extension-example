import '../../fixes/safe-storage';

import React from 'react';
import { createRoot } from 'react-dom/client';
import { setup } from '@mpt-extension/sdk';
import { BrowserRouter } from "react-router";

import App from './App';
import '../../style.scss';

setup((element: Element) => {
  const root = createRoot(element);

  root.render(
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
});
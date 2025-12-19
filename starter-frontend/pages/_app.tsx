import type { AppProps } from 'next/app';
import { Provider } from 'react-redux';
import { store } from '@/lib/store';
import '@/styles/globals.css';

import Layout from '@/components/Layout';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <Provider store={store}>
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </Provider>
  );
}


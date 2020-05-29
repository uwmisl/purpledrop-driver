import 'core-js/stable';
import 'regenerator-runtime/runtime';

import React from 'react';
import ReactDOM from 'react-dom';
import App from 'App';

/* Include global app styles here, so that it will over ride component's css styles*/
import './app.scss';

if (module.hot) {
    module.hot.accept();
}

if (process.env.NODE_ENV !== 'production') {
    console.log('Looks like we are in development mode!');
}

console.log('Env var test ===>', process.env.BASE_URL, process.env.BASE_URL_EXPAND);

ReactDOM.render(
  <App />,
  document.getElementById('root'),
);

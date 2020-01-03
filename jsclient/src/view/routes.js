import PageLayout from './components/page-layout';

// Individual pages
import IndexPage from './pages/landing-page';
import Splash from './components/splash-loader/index';
import MaintenancePage from './components/maintenance-layout/index';
import Pd from '../models/Pd';

function loadSpinner() {
    let $splashDiv = document.getElementById('splash');
    if (!$splashDiv) {
        $splashDiv = document.createElement('div');
        $splashDiv.setAttribute('id', 'splash');
        const $root = document.body.querySelector('#root');
        $root.appendChild($splashDiv);
    }
    m.render($splashDiv, m(Splash));
}
function hideSpinner() {
    let $splashDiv = document.getElementById('splash');
    if ($splashDiv) {
        m.render($splashDiv, null);
    }
}

const index_page = (compact) => {
    return {
        onmatch() {
            // Show Loader until the promise has been resolved or rejected.
            loadSpinner();
            return new Promise((resolve /*, reject*/) => {
                //Fetch all necessary data here
                Pd.init().then(() => resolve());
                // setTimeout(function() {
                //     //m.render($root, null);
                //     resolve();
                // }, 2000);
            }).catch(( e ) => {
                console.log('Error loading board config: ', e);
                // In case of server error we can show the maintenance page.
                return MaintenancePage;
            });
        },
        render(vnode) {
            hideSpinner();
            if (typeof vnode.tag === 'function') {
                //If onmatch returns a component or a promise that resolves to a component, comes here.
                return vnode;
            }
            return m(PageLayout, m(IndexPage, {compact: compact}));
        },
    };
};

const Routes = {
    '/splash': {
        render: function() {
            return m(PageLayout, m(Splash));
        },
    },
    '/index': index_page(false),
    '/compact': index_page(true),
};

const DefaultRoute = '/index';

export { Routes, DefaultRoute };

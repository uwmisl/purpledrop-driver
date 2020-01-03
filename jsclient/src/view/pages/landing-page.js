import ElectrodeBoard from '../components/electrode-board';
import {Pd} from '../../models/Pd';
import uwLogo from '../../images/uw-logo.png';
import mislLogo from '../../images/misl-logo.svg';
import Modal, {openModal, modalIsOpen} from '../components/modal';

console.log(modalIsOpen);

export default function() {
    return {
        view(vnode) {
            let usage = <div>
                <h2>Usage Instructions</h2>
                <ul>
                    <li style="text-align: left">Click to activate the highlighted electrodes under the cursor while deactivating all others.</li>
                    <li style="text-align: left">Shift-click to toggle electrodes under the curser without changing others. </li>
                    <li style="text-align: left">Arrow keys move all of the currently active electrodes together. </li>
                    <li style="text-align: left">Use the brush size buttons below to adjust the number of electrodes actuated with each click. </li>
                </ul>
            </div>;

            if (vnode.attrs.compact) {
                return <ElectrodeBoard board={Pd.board} />;
            } else {
                return ([
                    <div>
                        <div class='logobanner'>
                            <div><img class='uw-logo' src={uwLogo} /></div>
                            <div><img class='misl-logo' src={mislLogo} /></div>
                        </div>
                        <h1 style="text-align: center">Purple Drop: <span>Live View</span></h1>
                        <span style="float:right"><a href="#"
                            onclick={() => {
                                openModal({
                                    title: '',
                                    content: usage,
                                    buttons: [
                                        {id: 'close', text: 'Close'},
                                    ],
                                });
                            }}>Help</a></span>
                        <ElectrodeBoard board={Pd.board} />

                    </div>,
                    modalIsOpen() && m(Modal),
                ]);
            }
        },
    };
}
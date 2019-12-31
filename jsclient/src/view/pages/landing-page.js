import ElectrodeBoard from '../components/electrode-board';
import BoardConfig from '../../models/BoardConfig';
import {Pd, Video} from '../../models/Pd';

export default function() {
    return {
        oninit() {
            // Start periodic video information update polling
            let updateFn = () => {
                Video.update().then(() => { m.redraw(); });
                setTimeout(updateFn, 500);
            };

            setTimeout(updateFn, 1000);
        },

        view() {
            return (
                <div>
                    <h2>Purple Drop</h2>
                    <p>On the fly drop control</p>
                    <ElectrodeBoard board={BoardConfig.board} />
                </div>
            );
        },
    };
}
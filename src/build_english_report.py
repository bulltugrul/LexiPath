"""Full English edition of the LexiPath midterm report, using the same evidence."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import build_midterm_report as b
b.story=[];b.sections=[]
p,head,image,table=b.p,b.head,b.image,b.table
ROOT,OUT=b.ROOT,b.OUT
b.story.append(Spacer(1,35));p('LEXIPATH','TitleTR');p('Data Mining - Midterm Project','HeadTR')
p('Explainable English vocabulary tutoring: supervised response prediction, unsupervised performance patterns, and a learning-goal-specific teaching cycle.')
b.story.append(Spacer(1,25));table([['Group member','Student ID']]+b.members,[340,160])
p('Üsküdar University | 22 November 2026')
p('Submission: Python implementation, a 48-word practice environment, a four-word teaching pilot, fitted LR12 and K-Means models, annotated experiment outputs, a runnable notebook, and installation instructions.')
p('Ayşe in the screenshots is a synthetic demonstration learner. Real 24-hour retention is pending; neither the demonstration nor the automated tests is presented as a real learning-gain experiment. The interface remains Turkish.','SmallTR')
head('1. Problem, scope and requirement mapping')
p('The system identifies which word and learning goal need support, provides relevant instruction, and checks the result without assistance. Two fitted models serve narrow, explainable roles. Answer checks, teaching transitions, timing, and evidence interpretation are explicit application rules.')
table([['Required functionality','Implemented counterpart'],['Requirements and detailed scenario','Sections 1-2 distinguish the practice environment and the teaching pilot.'],['Supervised / unsupervised blocks','LR12 predicts correctness; K-Means clusters two-dimensional learner profiles.'],['Input / output schemas','Sections 5-6 specify fields, data types, target labels, probabilities, profiles and groups.'],['Text, audio and visual interaction','Writing, listening-writing, text-picture/audio-picture tasks, topic cards and visual instruction.'],['Subject success and change over time','Topic/format/phase counts, words and rounds; current target evidence and deadlines.'],['Patterns helping teaching','Individual-rate comparison and nearest source center provide a reasoned study suggestion.'],['Python, code and outputs','Functional explanations, code excerpts and measured outputs; complete source is in the archive.'],['Single archive and group information','All five members are on the cover; the archive contains report, code, models and required assets.']],[180,320])
p('The 48-word main environment supports interests, model-assisted practice and visual review. The four-word pilot provides a more detailed need → instruction → control evidence cycle. The two modules serve different purposes within one project: broad practice and detailed teaching evidence. Each keeps its own learner history.')
head('2. Detailed learner scenario: Ayşe')
for title,body in [
('Interests and scope','Ayşe selects animal, food and daily-life topic cards in the main environment. These cards collect content preferences. The pilot scope is fixed: cat, dog, apple and book.'),
('Measurement','The pilot asks four unassisted writing tasks, four common listening-writing controls, four text-picture and four audio-picture tasks. Writing comes first. Answers and predicted probabilities stay hidden during the control block.'),
('Need','Ayşe writes ca for cat and makes an audio-picture error for cat. Writing and audio-picture needs are separate. If multiple writing-review words are eligible, LR helps prioritize lower predicted correctness.'),
('Instruction','The writing card connects the word, image, meaning, audio and c+a+t spelling. A supported ca response receives a missing-t explanation and another attempt at the same goal. A second supported error pauses only that goal.'),
('Unassisted control','A supported correct response does not count as independent evidence. After spacing with other words, assistance is removed. Writing and picture-based goals are checked separately.'),
('Common model data','Four listening-writing tasks at the end of the first unassisted block produce a separate common control record. Only actual text-writing and listening-writing responses update the native model histories.'),
('Pattern and suggestion','The demonstration produces last-six text 6/6 and listening-writing 3/6. K-Means assigns Group 3. The individual rate difference motivates a suggestion to spend additional time on listening-writing.'),
('Delayed evidence','A real 24-hour wait follows the relevant control block. Same-session success does not establish permanent learning. Reteaching renews only the relevant goal’s evidence version; other valid results and deadlines remain intact.')]:p(title+': '+body)
head('3. ML task block diagram')
image(Path('outputs/diagrams/ml_blok_diyagrami_en.png'),390)
p('Figure 1. The two boxes are the actual learning tasks. Inputs and outputs are summarized briefly; detailed field schemas remain in Sections 5-6. Preference collection, answer matching, timing, teaching decisions and explanation rules are separate application mechanisms.')
table([['Training difference','LR: supervised','K-Means: unsupervised'],['Data supplied','Past features x and target-answer correctness y','Two observed profile proportions X'],['Learning objective','Reduce prediction loss against known y','Group similar profiles without expected group labels'],['New-record output','Probability of the next answer being correct','Provisional nearest-center group']],[130,185,185])
p('Visual linkage: LR prioritizes eligible visual-review words in the main environment. In the pilot, actual control errors trigger target-specific visual instruction. Picture choices and supported outcomes stay separate; subsequent appropriate unassisted responses connect instruction to the model histories. Text and audio responses connect visual teaching to the same learner scenario.')
head('4. Tutoring flow and decision ownership')
image(Path('outputs/diagrams/ogrenci_akisi_en.png'),410)
table([['Decision','Evidence and mechanism'],['Teaching need','Actual incorrect response + word/goal; a low probability alone is not a diagnosis.'],['Priority','LR p_correct ordering among eligible writing-review candidates.'],['Supported practice','First error: explained retry; second error: pause that goal only.'],['Learning evidence','Actual unassisted/delayed result pair, current target version and time condition.']],[155,345])
head('5. Supervised block: LR12 input and output')
desc=['Target English token','reverse_translate or listen','Number of all prior targets','Overall (correct+1)/(count+2)','Prior count for this word','Smoothed word correctness','Prior count in this format','Smoothed format correctness','Prior count for this word and format','Smoothed word-format correctness','Targets in the last 10 completed exercises','Smoothed correctness in that recent window']
table([['Field','Type','Meaning']]+[[r[0],r[1],meaning] for r,meaning in zip(b.fields,desc)],[226,55,219])
p('Output: p_correct is the probability of correctness in [0,1]; p_error=1-p_correct may be derived. The local trace stores features_before, model_version and history_after. Learner ID, the current response label, current duration and topic ID are not model inputs.')
p('OneHotEncoder transforms word/format; StandardScaler transforms numeric fields; LogisticRegression returns the class-1 probability. Transformations fit on TRAIN only. All tokens in one source exercise use the same pre-answer history; history updates only after all predictions for that exercise have been made.')
head('6. Unsupervised block: profiles, fitting and outputs')
table([['Field','Definition / rule'],['text_target_accuracy','Correct targets among the last six eligible text exercises / 6'],['listen_target_accuracy','Correct targets among the last six actual listening-writing exercises / 6'],['Availability','At least six records in each format; missing history is not treated as zero performance.'],['Preprocessing','StandardScaler fitted on TRAIN learner profiles only'],['Output','status, features, group.number, reference_center, reference_students']],[195,305])
p('For a multi-token source exercise, one profile target is selected without looking at correctness: the first alphabetic NOUN/PROPN, otherwise the first alphabetic token. This rule is specific to profile construction. LR training still uses all source token labels.')
p('K-Means receives no expected learner-group label. It learns centers from profile similarity. Using observed correctness to construct profile features does not turn this clustering task into supervised classification: the expected group y is absent. At runtime the fitted centers remain frozen and new profiles map to the nearest center.')
p('The suggestion is an explicit interpretation rule. If the learner’s text rate is higher, additional listening-writing practice is suggested; the reverse favors text writing. Equal rates produce no invented difference. The source center contextualizes the profile, while the learner’s own observations determine the direction. This interpretation layer offers an observation-based study suggestion.')
head('7. Source data and transfer to local tasks')
table([['Split','Learners','Exercises','Token targets']]+[[k.upper(),v['learners'],v['exercises'],v['targets']] for k,v in b.prep['summary'].items()],[110,100,140,150])
p('Duolingo SLAM 2018 en_es contains records from Spanish-speaking learners of English. The source label is 0=correct, 1=error; this project uses correct=1-source_error. Official temporal partitions and the same 200 learners are preserved. This is not a new-learner generalization experiment.')
p('The local catalog contains 48 words: 14 animals, 16 food/drink, 18 daily-life words. Added words were checked for TRAIN vocabulary and support in both source formats. Source exercises can contain multiple tokens; local tasks use one target and Turkish instructions. Connecting source listen to local single-word listening-writing remains a task-transfer assumption requiring validation.')
p('Durations are log-only because a source exercise duration and a local single-word duration are not directly equivalent. English WAVs were prepared using Microsoft Zira; pictures are local object symbols.')
p('The source is CC BY-NC 4.0. The archive preserves the license and citation and includes the derived 200-learner subset for reproduction. Raw archives and private access-form details are excluded. Data DOI: 10.7910/DVN/8SWHNO.')
head('8. Predictive contribution: simple methods to LR12')
rows=[['DEV method','Log loss','AUC','Accuracy']]
for label,m in [('Constant TRAIN rate',b.base['constant_train']),('Learner-history rate',b.base['learner_history']),('Word-format TRAIN rate',b.base['word_format_train']),('LR6',b.exp['original']),('LR12',b.exp['format_and_recent'])]:rows.append([label,f"{m['log_loss']:.4f}",f"{m['roc_auc_correct_positive']:.4f}",f"{100*m['accuracy_at_0_5']:.2f}%"])
table(rows,[230,90,90,90])
p('Lower log loss means smaller probability error. AUC is a ranking measure, not an accuracy percentage. LR12 improves recorded source DEV probability loss over the tested simple rates. Since 81.45% of DEV targets are already correct, reporting only 82.89% accuracy would overstate the contribution.')
p('At the fixed 0.50 threshold, LR12 catches 916 of 4,375 actual errors (20.94%) and raises 575 false alarms on correct answers. Teaching need therefore follows actual control responses rather than a probability threshold. Probability-based ordering is a separate policy; greater learning benefit has not been demonstrated.')
p('Selection uses DEV only. Historical LR6 TEST results are retained in the archive; there is no new blind TEST claim for the selected LR12. Selection on DEV and evaluation on later records of the same learners are important limits.')
head('9. Controlled feature experiments and calibration')
image(Path('outputs/presentation_plots/lr_run_metrics_en.png'),310)
table([['Candidate','Raw fields','DEV log loss'],['LR6',6,'0.41628'],['Add format history',10,'0.40265'],['Add recent history',8,'0.41397'],['Both groups: selected LR12',12,'0.40038']],[280,80,140])
p('Format history contributes most of the improvement. The recent window adds a smaller gain when combined with format history. No single candidate dominates every measure: the ten-bin calibration gap is 0.00446 for the format-only candidate and 0.00542 for LR12. Subgroup and learner-resampling analyses are exploratory because they use the same DEV set employed for selection.')
head('10. Comparing two, three and four clusters')
image(Path('outputs/presentation_plots/kmeans_selection_en.png'),280)
table([['k','Silhouette','Group sizes'],[2,'0.38860','77 / 123'],[3,'0.45691','40 / 68 / 92'],[4,'0.47378','18 / 64 / 42 / 76']],[70,150,280])
p('The 200 TRAIN learners occupy only 29 distinct profile points. Each dimension has seven possible last-six rates, so at most 49 positions exist. Duplicate positions remain in the training and scoring data. Among valid candidates with at least five learners per cluster, k=4 has the highest silhouette. Its 0.47378 score is not 47.378% accuracy; the difference from k=3 is approximately 0.0169.')
p('A single response changes a last-six rate by 16.7 percentage points. The profile is provisional. Source task difficulty and repeated local words differ, so the model does not establish four permanent learner types.')
head('11. Target-specific teaching and an explained retry')
image(Path('outputs/final_scenario/teaching.jpg'),310);image(Path('outputs/final_scenario/feedback.jpg'),270)
p('Figures 3-4. In the synthetic scenario, cat/writing receives image, audio, meaning and spelling support. A ca response gets a missing-t explanation and another attempt at the same goal. Copying a visible correct spelling is supported success only. These records keep native_history_used=false.','SmallTR')
head('12. Working common control, profile and suggestion')
image(Path('outputs/pilot_common_control/listen_write.jpg'),285);image(Path('outputs/final_scenario/profile_advice.jpg'),285)
p('Figures 5-6. The listening-writing task has audio and a text field but no picture, translation or letter cue. Actual answers produce eight text and eight listening-writing records. The last-six profile [1.00,0.50] maps to Group 3, whose source center is [0.9365,0.5437] with 42 learners. The suggestion uses the individual rate difference.','SmallTR')
head('13. Topic/goal evidence and delayed control')
image(Path('outputs/final_scenario/target_evidence.jpg'),345)
p('Operational measure: correct/total for a specified topic, goal and phase, together with the number of represented words. Ayşe’s unassisted checks can be correct while delayed evidence remains Pending. The zero retained-pair count must be read together with the missing delayed controls, not as 0% learning.')
table([['Unassisted','Delayed','Decision'],['Correct','Correct','Recalled at the delayed control'],['Correct','Wrong','Delayed recall failed; reteach'],['Wrong','Correct','Extra unassisted check; no automatic reteaching'],['Wrong','Wrong','Reteach']],[95,95,310])
p('The extra check is a separate third observation. Failure makes that goal eligible for reteaching; success records independent confirmation. Reteaching does not reuse an older delayed success as evidence for new instruction. Other learning goals retain their valid evidence and deadlines.')
head('14. Main environment: topic, format and round evidence')
image(Path('outputs/final_scenario/topic_evidence.jpg'),355)
p('The main environment separates diagnostic and practice records. In the example, animal/listening-writing practice is 0/2 from one word across two rounds. Those counts define the scope of the interpretation. High rates with little word coverage do not receive a strong-subject label either.')
p('For a word with at least three practice observations across two rounds, the last three actual results are shown. Two or more errors produce review priority; three correct responses produce repeated-correct evidence. This is a transparent application rule; its evaluation scope is discussed in Section 16. Otherwise the interface reports counts without a strong/weak judgment.')
p('Round/time evidence preserves first/last times, format, counts and round IDs. The cumulative graph summarizes observed correctness and is not by itself evidence of causal teaching benefit. Model probability, measured proportion and interpretation rule remain separate.')
head('15. Record structure and Python components')
table([['Component','Responsibility'],['features.py / experimental_features.py','Pre-answer fields, completed-exercise updates, last-ten window.'],['profiles.py','Last-six windows, label-independent source target selection, sufficient history.'],['tutor_engine.py','Model loading, history replay, LR scoring, main selection and visual review.'],['pilot.py','Sixteen-task measurement, goal-specific teaching, retries, common controls, evidence versions and timing.'],['learning_evidence.py','Topic/format/phase summaries, repeated-word evidence and individual-rate suggestions.'],['tutor_store.py / app_server.py','SQLite transactions, persistence, HTTP API and opaque audio/image asset keys.'],['web/static/*.js / HTML / CSS','Topics, questions, feedback, evidence, profiles and diagrams.'],['Training and notebook scripts','Subset preparation, supervised comparisons, cluster fitting, recorded-result visualization.'],['launch_tutor.py / demo_scenario.py','Local start-up and isolated synthetic demonstration.']],[190,310])
p('records contains id, stage, cycle, target_epoch, batch_id, word, skill, correct, submitted, at, assisted and native_history_used. Compatible writing also stores model_before/history_after. The common control uses skill=listen_write and assessment_role=common_control. attempts stores only compatible text/listen observations. Old actual answers remain in model history even when the teaching-evidence version changes.')
head('16. Validation, limits and operation')
p('56 automated tests pass. They cover feature boundaries, source profile selection, model integration, state transitions, four delayed decisions, evidence preservation, real-time gating, stale submissions, legacy records, native common-control routing and evidence summaries. The image-route regression test requests all eight opaque visual-bank URLs through HTTP.')
p('Browser screenshots use isolated synthetic data. Audio playback, a 4+0 to 4+1 native-history update, Group 3, topic evidence and reasoned suggestions were observed. The package is extracted into a separate directory and opened with empty stores; model/catalog/audio/image/diagram access and the full 8+8 pilot path are checked. Existing pinned dependencies are reused; a fresh internet pip installation is not claimed.')
p('Source DEV history contains at least 128 targets, median 941; the pilot starts at zero. Four synthetic correct writing responses can produce 96-98% LR probabilities, whose local calibration is not established. Elapsed time since review, teaching method and target-evidence version are not model inputs. LR is not a forgetting model, and a cluster is not CEFR.')
p('Real-student 24-hour retention and causal learning benefit remain unmeasured. Injected-clock tests exercise delayed transitions, while the real interface retains its time gate. Windows/Python 3.13: extract ZIP, run Kurulum.cmd and then Baslat.cmd. The installer tries python if py -3.13 fails. The main route is /; the teaching pilot is /pilot. Model training is not needed to launch the supplied estimators. Details are in CALISTIRMA.txt and TESLIM_KONTROLU.json.')
p('The project archive has been prepared, not automatically submitted to the instructor. A single group member must use the designated submission link and include all five members and IDs.')
head('17. Research context and references')
p('Zhu, M., Qiu, L., Zhou, J. (2026). Prompt-tuning for improving knowledge tracing in intelligent tutoring. Data Mining and Knowledge Discovery, 40:36. DOI: 10.1007/s10618-026-01208-9. The instructor-supplied 30-page paper introduces PLKT, LKM pre-training, PromEnc and experiments on four datasets. It is original method research, not a survey used as the project method.')
p('The paper motivates predicting future performance from learner interactions. This submission does not reimplement PLKT, prompt-tuning or a deep network. It implements the midterm supervised/unsupervised task design with explainable LR and K-Means. Earlier fine-tuning/fusion/sentiment exercises are not silently imported as mandatory components.')
p('Settles, B., Brust, C., Gustafson, E., Hagiwara, M., Madnani, N. (2018). Second Language Acquisition Modeling. Source data DOI: 10.7910/DVN/8SWHNO. https://sharedtask.duolingo.com/2018.html. This is a data/protocol citation, not a claim to reproduce another submitted system.')
p('Official scikit-learn documentation: LogisticRegression, ColumnTransformer, StandardScaler, OneHotEncoder, KMeans and silhouette_score. https://scikit-learn.org/stable/ . Project version: 1.9.1. Flask documentation: https://flask.palletsprojects.com/ . Python/SQLite provide local record storage. SLAM license and CITING text remain under LICENSES. Local audio uses Microsoft Zira; SVG assets are object symbols.')
head('18. Slide-style run results and error matrix')
audit=b.load('outputs/dev_feature_experiments/training_audit.json')['fits']
table([['Training run','Solver iterations','Fit seconds']]+[[label,audit[key]['iterations'][0],f"{audit[key]['fit_seconds']:.3f}"] for key,label in [('format_history','LR10: format'),('recent_history','LR8: recent'),('format_and_recent','LR12: both')]],[250,125,125])
image(Path('outputs/presentation_plots/lr12_confusion_en.png'),300)
p('Section 9 presents the LR comparison once. This table reports actual recorded solver iterations and fit times on the source machine. Per-iteration loss history was not recorded, so no artificial DistilBERT-style epoch curve is supplied. The confusion matrix exposes 916 detected errors, 3,459 missed errors and the false-alarm trade-off.','SmallTR')
head('19. Baseline contribution and cluster-selection plots')
image(Path('outputs/presentation_plots/baseline_loss_en.png'),270);image(Path('outputs/presentation_plots/kmeans_selection_en.png'),235)
p('LR12 improves recorded source DEV log loss relative to the tested rates. k=4 has the highest valid silhouette; lower inertia alone is not the selection criterion. The code and actual outputs are available in notebooks/LexiPath_Experiments.ipynb. It reads saved results, fits no model and opens no TEST examples.','SmallTR')
head('20. Detailed architecture and executed notebook')
image(Path('outputs/presentation_plots/technical_architecture_en.png'),365)
p('Inspired by the lecture data-flow style, fitting and inference are explicitly separated. Twelve raw LR columns become 1,382 encoded fields after categorical one-hot encoding and numeric scaling. The fitted coefficient array is (1,1382). K-Means uses 200×2 TRAIN profiles and the selected centers are 4×2. These internal stages expand the same two ML tasks rather than inventing additional learning blocks.')
p('Seven notebook code cells were executed in the project Python environment and their stdout and figures embedded. They cover data scope, feature variants, recorded solver iterations/times, DEV comparisons, k=2/3/4 selection and a synthetic profile/center comparison. Open it in Jupyter or VS Code with the project environment. The notebook does not fabricate epoch trajectories, new TEST evaluations or learning gains.')
explanations=[
'Pre-answer overall and word counts produce smoothed rates. A missing-history rate of 0.5 is an input initialization, not a model prediction.',
'Format, word-format and recent-window fields use the same function during training and live prediction.',
'After all current predictions are computed, a completed exercise updates counts and the last-ten deque.',
'A source target is selected without using correctness. Chronology is retained and each exercise contributes at most one profile observation.',
'Completed history is replayed, the 12-column frame follows the model contract, and predict_proba returns the class-1 probability.',
'Diagnostic and practice sessions follow different policies. LR ranks candidates while round composition, spacing and repeat limits are explicit rules.',
'Incorrect words supported by the image bank become candidates. LR ranks their text-review probabilities, not their visual-answer probabilities.',
'The sixteen-task plan includes separate common listening-writing controls. A paused writing word is skipped in the common control; legacy plans remain intact.',
'A typed answer is normalized and matched to one expected word. listen_write routes to listen and writing routes to reverse_translate; picture choices do not enter native histories.',
'The first error retries the same goal. Supported success or a pause advances to the next goal. Supported success does not become independent evidence.',
'Only the current goal-evidence version is considered. Wrong/correct requires an extra independent check; delayed correctness alone does not overwrite the earlier result.',
'Only reteach goals receive new evidence versions. Other deadlines and results remain valid, and raw records are preserved.',
'Individual rates are compared without inventing a difference on equality. Source-center context and the short-window limitation are stated.',
'Topic, format and phase are separated. Counts, word coverage and rounds accompany rates; only repeated evidence yields a word-level interpretation.',
'BEGIN IMMEDIATE protects an atomic state update. Exceptions roll back. Stale task IDs are rejected at the application layer.',
'Models and separate SQLite stores are connected to main/pilot routes. Opaque audio/image keys avoid putting the answer word in the current asset URL.',
'Fitting uses TRAIN and comparison uses DEV. The original model remains a reference and TEST is not used for feature development.',
'Only TRAIN profiles enter the k=2/3/4 comparison. Fixed seeds/restarts and the highest valid silhouette determine the selected model.']
index=b.load('outputs/report_assets/code_index.json')
for i,(item,explanation) in enumerate(zip(index,explanations),1):
 if i not in {1,2,4,5,7,9,11,12,13,15}:continue
 head(f"Appendix A{i:02d}. {item['file']} / {item['function']}")
 image(Path(f'outputs/report_assets/code_{i:02d}.png'),390);p(explanation)
 p(f"Actual source excerpt: src/{item['file']}, lines {item['start']}-{item['end']}. Long lines are wrapped for readability. The excerpt may show only part of a function; the complete source is included in the archive. Original source comments remain unchanged.",'SmallTR')
head('Appendix A. Other functional sections')
for i,(item,explanation) in enumerate(zip(index,explanations),1):
 if i not in {1,2,4,5,7,9,11,12,13,15}:p(f"{item['file']} / {item['function']}: {explanation}")
head('Appendix B. Reading the code and output package')
p('Application logic: tutor_engine and pilot; measured evidence and suggestions: learning_evidence; persistence: tutor_store; routes: app_server; start-up: launch_tutor. app.js handles the main environment and pilot.js the goal cycle. HTML provides roots and style.css layout.')
p('Training: prepare_slam_subset preserves learner histories with seed=42; train_logistic is the historical LR6 protocol; compare_dev_baselines evaluates rates; run_dev_feature_experiments produces the controlled LR variants; prepare_profiles/train_kmeans construct and fit profile groups. Rendering scripts produce diagrams, recorded plots and reports. demo_scenario creates an explicitly synthetic learner in a separate database.')
p('Output folders: logistic_first_run stores historical LR6; dev_baseline_comparison stores DEV rate comparisons; dev_feature_experiments stores fitted feature candidates and audits; kmeans_first_run stores k selection and centers; diagrams stores task and scenario figures; final_scenario stores synthetic outputs/screenshots; presentation_plots stores the new explanatory charts. notebooks contains the executed review notebook. Working paths required by model loading are preserved.')
p('test_*.py files verify implementation behavior, not student learning. Prepared source TEST records are retained only to reproduce the original historical protocol. No new selected-LR12 TEST performance is reported. KOD_HARITASI.txt indexes functions. Every member should be able to explain the model tasks, field schemas and code changes. Presentation: 27 November 2026, 14:40, B-Yunus Emre.')
def footer(canvas,doc):
 canvas.setStrokeColor(colors.HexColor('#D7E2E8'));canvas.line(43,38,552,38)
 canvas.setFont('Arial',8);canvas.setFillColor(colors.HexColor('#486070'));canvas.drawString(43,25,'LexiPath | Data Mining Midterm | English edition | 22 Nov 2026');canvas.drawRightString(552,25,str(doc.page))
doc=SimpleDocTemplate(str(OUT/'LexiPath_Midterm_Report_EN.pdf'),pagesize=A4,rightMargin=43,leftMargin=43,topMargin=43,bottomMargin=48,title='LexiPath - Data Mining Midterm - English edition',author='; '.join(name for name,_ in b.members))
doc.build(b.story,onFirstPage=footer,onLaterPages=footer)
print(OUT/'LexiPath_Midterm_Report_EN.pdf')
